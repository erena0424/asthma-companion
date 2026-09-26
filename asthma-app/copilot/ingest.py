"""Manifest-driven ingestion for approved asthma knowledge sources."""

from __future__ import annotations

import argparse
import hashlib
import io
import json
import math
import re
from collections import Counter
from dataclasses import dataclass
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

import httpx
from bs4 import BeautifulSoup
from pypdf import PdfReader

PROJECT_ROOT = Path(__file__).resolve().parent.parent
DEFAULT_MANIFEST = PROJECT_ROOT / "knowledge" / "sources.json"
DEFAULT_OUTPUT = PROJECT_ROOT / "knowledge" / "generated" / "chunks.json"
ALLOWED_REMOTE_HOSTS = {
    "cdc": {"cdc.gov", "www.cdc.gov"},
    "nhlbi": {"nhlbi.nih.gov", "www.nhlbi.nih.gov"},
    "epa airnow": {"airnow.gov", "www.airnow.gov"},
}


@dataclass(frozen=True)
class ContentBlock:
    section: str | None
    text: str


MIN_CHUNK_CHARS = 100
MIN_CHUNK_WORDS = 14

ADVICE_TYPE_RULES: dict[str, tuple[str, ...]] = {
    "emergency": (
        "emergency",
        "danger sign",
        "call 911",
        "hospital",
        "very short of breath",
        "trouble walking",
        "trouble talking",
    ),
    "action_plan": ("action plan", "green zone", "yellow zone", "red zone"),
    "air_quality": (
        "air quality",
        "air pollution",
        "aqi",
        "particulate matter",
        "pm2.5",
    ),
    "wildfire": ("wildfire", "fire smoke", "smoke event", "smoky"),
    "adherence": (
        "exactly as prescribed",
        "use your inhaler",
        "using an asthma inhaler",
        "take asthma medication",
        "take medicine",
    ),
    "exercise": (
        "exercise",
        "physical activity",
        "physical activities",
        "exertion",
        "run outdoors",
    ),
}

TRIGGER_TAG_RULES: dict[str, tuple[str, ...]] = {
    "air_quality": ("air quality", "air pollution", "aqi", "pm2.5"),
    "wildfire": ("wildfire", "fire smoke", "smoke event", "smoky"),
    "tobacco_smoke": ("tobacco smoke", "cigarette smoke", "secondhand smoke"),
    "pollen": ("pollen", "tree pollen", "grass pollen", "weed pollen"),
    "mold": ("mold", "damp"),
    "dust_mites": ("dust mite", "dust mites"),
    "pets": ("pet", "pets", "furry"),
    "pests": ("cockroach", "cockroaches", "rodent", "mouse", "mice"),
    "exercise": ("exercise", "physical activity", "exertion"),
    "cold_air": ("cold air", "cold, dry air"),
    "humidity": ("humidity", "humid"),
    "infection": ("infection", "flu", "cold", "rsv"),
    "action_plan": ("action plan",),
    "emergency_signs": ("danger sign", "call 911", "emergency"),
    "adherence": ("exactly as prescribed", "use your inhaler", "take medicine"),
}


def ingest_manifest(
    manifest_path: Path = DEFAULT_MANIFEST,
    output_path: Path = DEFAULT_OUTPUT,
) -> list[dict[str, Any]]:
    manifest = json.loads(manifest_path.read_text())
    chunks: list[dict[str, Any]] = []
    for source in manifest["sources"]:
        if not source.get("enabled", False):
            continue
        content = _read_source(source, manifest_path.parent)
        blocks = _extract_blocks(content, source["format"])
        document_hash = hashlib.sha256(content).hexdigest()
        excluded_sections = {
            value.casefold() for value in source.get("exclude_sections", [])
        }
        for index, (section, body) in enumerate(chunk_blocks(blocks)):
            if section and section.casefold() in excluded_sections:
                continue
            if not _is_useful_chunk(body):
                continue
            tags, advice_types = _chunk_metadata(source, section, body)
            if not advice_types:
                continue
            chunk_hash = hashlib.sha256(body.encode("utf-8")).hexdigest()
            chunks.append(
                {
                    "chunk_id": f"{source['id']}:{index}:{chunk_hash[:12]}",
                    "title": source["title"],
                    "body": body,
                    "publisher": source["publisher"],
                    "source_url": source.get("url"),
                    "section": section or source.get("section"),
                    "version": source.get("version"),
                    "document_hash": document_hash,
                    "tags": tags,
                    "audience": source["audience"],
                    "medication_change_allowed": bool(
                        source.get("medication_change_allowed", False)
                    ),
                    "advice_types": advice_types,
                }
            )
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(chunks, indent=2, ensure_ascii=False) + "\n")
    return chunks


def _is_useful_chunk(body: str) -> bool:
    words = re.findall(r"\b[\w'-]+\b", body)
    return len(body) >= MIN_CHUNK_CHARS and len(words) >= MIN_CHUNK_WORDS


def _chunk_metadata(
    source: dict[str, Any],
    section: str | None,
    body: str,
) -> tuple[list[str], list[str]]:
    allowed_types = set(source["advice_types"])
    if source["audience"] == "clinician":
        return list(source.get("tags", [])), sorted(allowed_types)

    searchable = f"{source['title']} {section or ''} {body}".casefold()
    advice_types = {
        advice_type
        for advice_type, phrases in ADVICE_TYPE_RULES.items()
        if advice_type in allowed_types
        and any(phrase in searchable for phrase in phrases)
    }
    if "daily" in allowed_types:
        advice_types.add("daily")

    tags = {
        tag
        for tag, phrases in TRIGGER_TAG_RULES.items()
        if any(phrase in searchable for phrase in phrases)
    }
    tags.update(
        tag
        for tag in source.get("tags", [])
        if tag.casefold().replace("_", " ") in searchable
    )
    if "daily" in advice_types:
        tags.add("self_management")
    return sorted(tags), sorted(advice_types)


def _read_source(source: dict[str, Any], manifest_dir: Path) -> bytes:
    if source["format"].startswith("local_"):
        path = (manifest_dir / source["path"]).resolve()
        if manifest_dir.resolve() not in path.parents:
            raise ValueError(f"Local source escapes knowledge directory: {path}")
        return path.read_bytes()

    url = source["url"]
    _validate_remote_url(source["publisher"], url)
    response = httpx.get(url, timeout=30, follow_redirects=True)
    response.raise_for_status()
    _validate_remote_url(source["publisher"], str(response.url))
    return response.content


def _validate_remote_url(publisher: str, url: str) -> None:
    parsed = urlparse(url)
    allowed = ALLOWED_REMOTE_HOSTS.get(publisher.lower(), set())
    if parsed.scheme != "https" or parsed.hostname not in allowed:
        raise ValueError(
            f"Remote source is not allowlisted for {publisher}: {parsed.hostname}"
        )


def _extract_blocks(content: bytes, source_format: str) -> list[ContentBlock]:
    normalized = source_format.removeprefix("local_")
    if normalized == "pdf":
        return _pdf_blocks(content)
    if normalized == "html":
        return _html_blocks(content)
    if normalized == "text":
        return _text_blocks(content.decode("utf-8"))
    raise ValueError(f"Unsupported source format: {source_format}")


def _html_blocks(content: bytes) -> list[ContentBlock]:
    soup = BeautifulSoup(content, "html.parser")
    for element in soup(
        ["script", "style", "nav", "footer", "header", "aside", "form", "button", "svg"]
    ):
        element.decompose()
    root = (
        soup.find("main")
        or soup.find("article")
        or soup.select_one(".main-content")
        or soup.body
        or soup
    )
    blocks: list[ContentBlock] = []
    current_section: str | None = None
    seen: set[tuple[str | None, str]] = set()
    for element in root.find_all(["h1", "h2", "h3", "h4", "p", "li"]):
        if element.name in {"p", "li"} and element.find_parent(["p", "li"]):
            continue
        text = _clean_text(element.get_text(" ", strip=True))
        if not text or _is_navigation_text(text):
            continue
        if element.name.startswith("h"):
            current_section = text
            continue
        key = (current_section, text)
        if key not in seen:
            blocks.append(ContentBlock(current_section, text))
            seen.add(key)
    return blocks


def _pdf_blocks(content: bytes) -> list[ContentBlock]:
    pages = [
        (page.extract_text(extraction_mode="layout") or "")
        for page in PdfReader(io.BytesIO(content)).pages
    ]
    line_counts = Counter(
        _clean_text(line)
        for page in pages
        for line in page.splitlines()
        if _clean_text(line)
    )
    repeated_threshold = max(2, math.ceil(len(pages) * 0.4))
    repeated_lines = {
        line
        for line, count in line_counts.items()
        if count >= repeated_threshold and len(line) < 160
    }
    blocks: list[ContentBlock] = []
    current_section: str | None = None
    for page in pages:
        page_lines = _repair_pdf_line_breaks(page.splitlines())
        paragraph_lines: list[str] = []

        def flush_paragraph() -> None:
            if paragraph_lines:
                text = _clean_text(" ".join(paragraph_lines))
                if text and not _is_navigation_text(text):
                    blocks.append(ContentBlock(current_section, text))
                paragraph_lines.clear()

        for raw_line in page_lines:
            line = _clean_text(raw_line)
            if (
                not line
                or line in repeated_lines
                or re.fullmatch(r"(?:page\s+)?\d+(?:\s+of\s+\d+)?", line, re.IGNORECASE)
            ):
                flush_paragraph()
                continue
            if _looks_like_heading(line):
                flush_paragraph()
                current_section = line
            else:
                paragraph_lines.append(line)
        flush_paragraph()
    return blocks


def _text_blocks(text: str) -> list[ContentBlock]:
    blocks: list[ContentBlock] = []
    current_section: str | None = None
    for paragraph in re.split(r"\n\s*\n", text):
        cleaned = _clean_text(paragraph)
        if not cleaned:
            continue
        if _looks_like_heading(cleaned):
            current_section = cleaned
        else:
            blocks.append(ContentBlock(current_section, cleaned))
    return blocks


def _clean_text(text: str) -> str:
    cleaned = re.sub(r"\s+", " ", text).strip()
    # Some tagged PDFs visually separate the first letter of EXHALE headings.
    for fragmented, repaired in {
        "E ducation": "Education",
        "X -tinguishing": "X-tinguishing",
        "H ome": "Home",
        "A chievement": "Achievement",
        "L inkages": "Linkages",
        "E nvironmental": "Environmental",
    }.items():
        cleaned = cleaned.replace(fragmented, repaired)
    return re.sub(r"(https?://\S+/)\s+(?=[A-Za-z0-9])", r"\1", cleaned)


def _repair_pdf_line_breaks(lines: list[str]) -> list[str]:
    repaired: list[str] = []
    index = 0
    while index < len(lines):
        current = lines[index]
        if index + 1 < len(lines):
            next_line = lines[index + 1]
            current_clean = _clean_text(current)
            next_clean = _clean_text(next_line)
            last_word = current_clean.split()[-1] if current_clean else ""
            split_fragment = (
                next_clean[:1].islower()
                and (
                    len(current_clean) <= 3
                    or len(last_word) <= 3
                    and last_word[:1].isupper()
                )
            )
            if split_fragment:
                repaired.append(f"{current.rstrip()}{next_line.lstrip()}")
                index += 2
                continue
        repaired.append(current)
        index += 1
    return repaired


def _is_navigation_text(text: str) -> bool:
    normalized = text.casefold()
    navigation_phrases = (
        "skip directly to site content",
        "on this page",
        "back to top",
        "share this page",
        "print this page",
        "was this page helpful",
        "last reviewed",
        "last updated",
        "related pages",
    )
    return any(normalized == phrase or normalized.startswith(f"{phrase}:") for phrase in navigation_phrases)


def _looks_like_heading(text: str) -> bool:
    if len(text) < 4 or len(text) > 120 or text.endswith((".", "?", "!", ";")):
        return False
    words = text.split()
    if not words or len(words) > 14:
        return False
    letters = [char for char in text if char.isalpha()]
    uppercase_ratio = (
        sum(char.isupper() for char in letters) / len(letters) if letters else 0
    )
    title_ratio = sum(word[:1].isupper() for word in words) / len(words)
    return uppercase_ratio > 0.7 or title_ratio > 0.75


def _split_oversized_block(block: ContentBlock, target_chars: int) -> list[ContentBlock]:
    if len(block.text) <= target_chars:
        return [block]
    sentences = [
        sentence.strip()
        for sentence in re.split(r"(?<=[.!?])\s+", block.text)
        if sentence.strip()
    ]
    pieces: list[str] = []
    current: list[str] = []
    for sentence in sentences:
        if len(sentence) > target_chars:
            words = sentence.split()
            for word in words:
                if current and len(" ".join([*current, word])) > target_chars:
                    pieces.append(" ".join(current))
                    current = []
                current.append(word)
        elif current and len(" ".join([*current, sentence])) > target_chars:
            pieces.append(" ".join(current))
            current = [sentence]
        else:
            current.append(sentence)
    if current:
        pieces.append(" ".join(current))
    return [ContentBlock(block.section, piece) for piece in pieces]


def chunk_blocks(
    blocks: list[ContentBlock],
    *,
    target_chars: int = 1400,
    overlap_chars: int = 180,
) -> list[tuple[str | None, str]]:
    expanded = [
        piece
        for block in blocks
        for piece in _split_oversized_block(block, target_chars)
    ]
    chunks: list[tuple[str | None, str]] = []
    current: list[ContentBlock] = []
    current_section: str | None = None

    def flush() -> None:
        nonlocal current
        if not current:
            return
        body_parts = [block.text for block in current]
        if current_section:
            body_parts.insert(0, current_section)
        chunks.append((current_section, "\n\n".join(body_parts)))
        overlap: list[ContentBlock] = []
        overlap_length = 0
        for block in reversed(current):
            if overlap_length + len(block.text) > overlap_chars:
                break
            overlap.insert(0, block)
            overlap_length += len(block.text)
        current = overlap

    for block in expanded:
        if current and block.section != current_section:
            flush()
            current = []
        current_section = block.section
        candidate_length = sum(len(item.text) + 2 for item in current) + len(block.text)
        if current and candidate_length > target_chars:
            flush()
        current.append(block)
    flush()
    return chunks


def chunk_text(text: str, *, target_chars: int = 1400, overlap_chars: int = 180) -> list[str]:
    """Compatibility wrapper used by tests and approved local plain-text sources."""
    return [
        body
        for _, body in chunk_blocks(
            _text_blocks(text),
            target_chars=target_chars,
            overlap_chars=overlap_chars,
        )
    ]


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--manifest", type=Path, default=DEFAULT_MANIFEST)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    args = parser.parse_args()
    chunks = ingest_manifest(args.manifest, args.output)
    print(f"Wrote {len(chunks)} chunks to {args.output}")


if __name__ == "__main__":
    main()

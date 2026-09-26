"""Offline tests for manifest-driven medical knowledge ingestion."""

from __future__ import annotations

import json

import pytest

from copilot.ingest import DEFAULT_MANIFEST, chunk_text, ingest_manifest


def test_default_manifest_has_audience_safety_and_required_topics():
    manifest = json.loads(DEFAULT_MANIFEST.read_text())
    enabled = [source for source in manifest["sources"] if source["enabled"]]
    nhlbi = next(source for source in enabled if source["publisher"] == "NHLBI")
    covered_types = {
        advice_type
        for source in enabled
        for advice_type in source["advice_types"]
    }

    assert nhlbi["audience"] == "clinician"
    assert nhlbi["advice_types"] == ["clinical_reference"]
    assert all(source["medication_change_allowed"] is False for source in enabled)
    assert {
        "emergency",
        "action_plan",
        "air_quality",
        "wildfire",
        "adherence",
        "exercise",
    } <= covered_types


def test_local_manifest_produces_stable_provenance_chunks(tmp_path):
    source = tmp_path / "approved.txt"
    source.write_text(
        "Air quality precautions\n\n"
        "Air pollution and a high AQI may worsen breathing symptoms. "
        "Check the local air quality report and reduce exposure to polluted outdoor air."
    )
    manifest = tmp_path / "sources.json"
    manifest.write_text(
        json.dumps(
            {
                "sources": [
                    {
                        "id": "approved-test",
                        "publisher": "Test Publisher",
                        "title": "Approved Test",
                        "path": "approved.txt",
                        "format": "local_text",
                        "version": "1",
                        "tags": ["air_quality"],
                        "audience": "patient",
                        "medication_change_allowed": False,
                        "advice_types": ["air_quality"],
                        "enabled": True,
                    }
                ]
            }
        )
    )
    output = tmp_path / "generated" / "chunks.json"

    first = ingest_manifest(manifest, output)
    second = ingest_manifest(manifest, output)

    assert first == second
    assert first[0]["chunk_id"].startswith("approved-test:0:")
    assert first[0]["publisher"] == "Test Publisher"
    assert first[0]["audience"] == "patient"
    assert first[0]["medication_change_allowed"] is False
    assert first[0]["advice_types"] == ["air_quality"]
    assert len(first[0]["document_hash"]) == 64


def test_local_manifest_cannot_escape_knowledge_directory(tmp_path):
    outside = tmp_path.parent / "outside.txt"
    outside.write_text("not approved")
    manifest = tmp_path / "sources.json"
    manifest.write_text(
        json.dumps(
            {
                "sources": [
                    {
                        "id": "escape",
                        "publisher": "Test",
                        "title": "Escape",
                        "path": "../outside.txt",
                        "format": "local_text",
                        "enabled": True,
                    }
                ]
            }
        )
    )

    with pytest.raises(ValueError, match="escapes knowledge directory"):
        ingest_manifest(manifest, tmp_path / "chunks.json")


def test_chunk_text_never_splits_inside_paragraph_tokens():
    text = "\n\n".join(["A" * 700, "B" * 700, "C" * 700])
    chunks = chunk_text(text, target_chars=1000, overlap_chars=100)

    assert len(chunks) == 3
    assert chunks == ["A" * 700, "B" * 700, "C" * 700]


def test_html_ingestion_keeps_headings_and_removes_navigation(tmp_path):
    source = tmp_path / "patient.html"
    source.write_text(
        "<html><body><nav>Home Navigation</nav><a id='main-content'></a><article>"
        "<h2>Emergency Signs</h2>"
        "<p>Trouble walking or talking because of shortness of breath can be an "
        "asthma danger sign. Seek emergency help immediately and call 911 rather "
        "than waiting for an online response.</p>"
        "</article><footer>Footer Links</footer></body></html>"
    )
    manifest = tmp_path / "sources.json"
    manifest.write_text(
        json.dumps(
            {
                "sources": [
                    {
                        "id": "patient-test",
                        "publisher": "Test Publisher",
                        "title": "Patient Test",
                        "path": "patient.html",
                        "format": "local_html",
                        "version": "1",
                        "tags": ["emergency"],
                        "audience": "patient",
                        "medication_change_allowed": False,
                        "advice_types": ["emergency"],
                        "enabled": True,
                    }
                ]
            }
        )
    )

    chunks = ingest_manifest(manifest, tmp_path / "chunks.json")

    assert chunks[0]["section"] == "Emergency Signs"
    assert chunks[0]["body"].startswith("Emergency Signs")
    assert "Home Navigation" not in chunks[0]["body"]
    assert "Footer Links" not in chunks[0]["body"]


def test_ingestion_drops_short_fragments_and_assigns_chunk_topics(tmp_path):
    source = tmp_path / "topics.html"
    source.write_text(
        "<main>"
        "<h2>Navigation fragment</h2><p>Read more.</p>"
        "<h2>Exercise precautions</h2>"
        "<p>Physical activity and exercise can trigger breathing symptoms for some "
        "people. Discuss safe activity with a healthcare professional and follow "
        "your clinician-authored asthma action plan.</p>"
        "<h2>Publications</h2><p>Wildfire smoke publication directory with many "
        "external links and resource titles that should not become advice context "
        "even though this paragraph is long enough to pass the size threshold.</p>"
        "</main>"
    )
    manifest = tmp_path / "sources.json"
    manifest.write_text(
        json.dumps(
            {
                "sources": [
                    {
                        "id": "topic-test",
                        "publisher": "Test Publisher",
                        "title": "Patient Management",
                        "path": "topics.html",
                        "format": "local_html",
                        "version": "1",
                        "tags": ["self_management", "exercise", "action_plan"],
                        "exclude_sections": ["Publications"],
                        "audience": "patient",
                        "medication_change_allowed": False,
                        "advice_types": ["daily", "exercise", "action_plan"],
                        "enabled": True,
                    }
                ]
            }
        )
    )

    chunks = ingest_manifest(manifest, tmp_path / "chunks.json")

    assert len(chunks) == 1
    assert chunks[0]["section"] == "Exercise precautions"
    assert chunks[0]["advice_types"] == ["action_plan", "daily", "exercise"]
    assert "exercise" in chunks[0]["tags"]

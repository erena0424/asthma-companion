"""Build structured asthma episodes from calendar + environment + symptoms.

Memory vs risk boundary:
  - Embedding / FTS text = life-situation context (events, locations, activity types).
  - Environment + outcomes stay in metadata as evidence for the LLM, not retrieval keys.
  - ML forecast owns risk_context (pollen, AQI, symptoms, contributing factors).
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import date
from typing import Any

_OUTDOOR_RE = re.compile(
    r"\b(outdoor|outside|soccer|football|run|running|jog|walk|walking|trail|"
    r"hike|picnic|farmers?\s*market|club\s*fair|intramural|field|park)\b",
    re.I,
)
_EXERCISE_RE = re.compile(
    r"\b(soccer|football|run|running|jog|gym|cardio|weights?|workout|exercise|"
    r"trail|hike|practice|scrimmage|pickup)\b",
    re.I,
)
_LECTURE_RE = re.compile(r"\b(lecture|seminar|class|course)\b", re.I)
_LAB_RE = re.compile(r"\b(lab|laboratory)\b", re.I)
_EXAM_RE = re.compile(r"\b(exam|midterm|final|quiz)\b", re.I)
_STUDY_RE = re.compile(r"\b(study|homework|office\s*hours)\b", re.I)
_GYM_RE = re.compile(r"\b(gym|cardio|weights?|workout)\b", re.I)
_COLD_RE = re.compile(r"\b(cold|freezing|winter)\b", re.I)
_INDOOR_CLASS_TOKEN = re.compile(r"\b(stat|bio|chem|cs|math|physics)\b", re.I)


@dataclass(frozen=True)
class BuiltEpisode:
    episode_date: date
    summary_text: str
    metadata: dict[str, Any]
    kind: str = "retrospective"


def _calendar_titles(calendar: list[dict[str, Any]] | None, legacy_event: str | None = None) -> list[str]:
    titles: list[str] = []
    for event in calendar or []:
        title = str(event.get("title") or "").strip()
        if title:
            titles.append(title)
    if legacy_event and legacy_event.strip() and legacy_event.strip() not in titles:
        titles.append(legacy_event.strip())
    return titles


def _locations(calendar: list[dict[str, Any]] | None) -> list[str]:
    locations: list[str] = []
    for event in calendar or []:
        loc = str(event.get("location") or "").strip()
        if loc and loc not in locations:
            locations.append(loc)
    return locations


def _event_category(title: str) -> str:
    if _LAB_RE.search(title):
        return "lab"
    if _EXAM_RE.search(title):
        return "exam"
    if _LECTURE_RE.search(title) or _INDOOR_CLASS_TOKEN.search(title):
        return "lecture"
    if _STUDY_RE.search(title):
        return "study"
    if _OUTDOOR_RE.search(title) and _EXERCISE_RE.search(title):
        return "outdoor_exercise"
    if _GYM_RE.search(title) or (_EXERCISE_RE.search(title) and not _OUTDOOR_RE.search(title)):
        return "indoor_exercise"
    if _OUTDOOR_RE.search(title):
        return "outdoor_other"
    return "other"


def _event_categories(titles: list[str]) -> list[str]:
    cats = [_event_category(title) for title in titles]
    return list(dict.fromkeys(cats)) if cats else ["other"]


def _primary_activity(titles: list[str]) -> str:
    if not titles:
        return "daily check-in"
    return titles[0]


def _legacy_category(activity: str, titles: list[str]) -> str:
    """Single rollup category kept for older consumers / insights grouping."""
    cats = _event_categories(titles or [activity])
    if "outdoor_exercise" in cats:
        return "outdoor_exercise"
    if "outdoor_other" in cats:
        return "outdoor_other"
    if "indoor_exercise" in cats:
        return "indoor_exercise"
    if any(c in cats for c in ("lecture", "lab", "exam", "study")):
        return "indoor_class"
    return "indoor_other"


def _activity_type_phrases(categories: list[str]) -> list[str]:
    mapping = {
        "lecture": "indoor academic activity",
        "lab": "indoor laboratory activity",
        "exam": "indoor academic exam",
        "study": "indoor study activity",
        "indoor_exercise": "indoor physical activity",
        "outdoor_exercise": "outdoor physical activity",
        "outdoor_other": "outdoor activity",
        "other": "general daily activity",
    }
    return [mapping.get(cat, "general daily activity") for cat in categories]


def _pollen_label(environment: dict[str, Any]) -> str | None:
    levels = [
        str(environment.get(key) or "").strip().lower()
        for key in ("tree_pollen", "grass_pollen", "weed_pollen")
    ]
    levels = [level for level in levels if level]
    if not levels:
        return None
    priority = ("very high", "high", "moderate", "low", "none")
    for label in priority:
        if any(level == label for level in levels):
            return label
    return levels[0]


def _exposure_factors(
    *,
    category: str,
    activity: str,
    environment: dict[str, Any],
    triggers: list[str] | None = None,
) -> list[str]:
    """Stored as metadata evidence — not used in the embedding text."""
    factors: list[str] = []
    blob = f"{category} {activity} {' '.join(triggers or [])}"
    if category.startswith("outdoor") or _OUTDOOR_RE.search(blob):
        factors.append("outdoor")
    else:
        factors.append("indoor")
    if _EXERCISE_RE.search(blob) or category.endswith("exercise"):
        factors.append("high_exertion")
    temp = environment.get("temperature")
    if isinstance(temp, (int, float)) and temp <= 5:
        factors.append("cold_air")
    elif _COLD_RE.search(blob):
        factors.append("cold_air")
    pollen = _pollen_label(environment)
    if pollen in {"high", "very high"}:
        factors.append("high_pollen")
    aqi = environment.get("aqi")
    if isinstance(aqi, (int, float)) and aqi >= 3:
        factors.append("elevated_aqi")
    for trigger in triggers or []:
        normalized = trigger.strip().lower().replace(" ", "_")
        if normalized and normalized not in factors:
            factors.append(normalized)
    return list(dict.fromkeys(factors))


def _symptom_labels(
    *,
    day_symp: bool = False,
    night_symp: bool = False,
    limit_activity: bool = False,
    extra: list[str] | None = None,
) -> list[str]:
    labels: list[str] = []
    if day_symp:
        labels.append("daytime symptoms")
    if night_symp:
        labels.append("nighttime symptoms")
    if limit_activity:
        labels.append("activity limitation")
    for item in extra or []:
        if item and item not in labels:
            labels.append(item)
    return labels


def _environment_payload(environment: dict[str, Any]) -> dict[str, Any]:
    pollen = _pollen_label(environment)
    payload: dict[str, Any] = {}
    if environment.get("temperature") is not None:
        payload["temperature"] = environment.get("temperature")
    if pollen:
        payload["pollen"] = pollen
    if environment.get("aqi") is not None:
        payload["aqi"] = environment.get("aqi")
    if environment.get("humidity") is not None:
        payload["humidity"] = environment.get("humidity")
    if environment.get("pm2_5") is not None:
        payload["pm2_5"] = environment.get("pm2_5")
    return payload


def build_memory_summary_text(
    *,
    events: list[str],
    locations: list[str],
    event_categories: list[str],
    prospective: bool = False,
) -> str:
    """Embedding / FTS text: life situation only (no pollen/AQI/outcomes/risk factors)."""
    header = "Tomorrow's activities:" if prospective else "Activities:"
    lines = [header]
    if events:
        for title in events:
            lines.append(f"- {title}")
    else:
        lines.append("- daily check-in / no calendar events")
    if locations:
        lines.append("Locations:")
        for loc in locations:
            lines.append(f"- {loc}")
    phrases = _activity_type_phrases(event_categories or ["other"])
    lines.append("Activity types:")
    for phrase in phrases:
        lines.append(f"- {phrase}")
    return "\n".join(lines)


def build_summary_text(metadata: dict[str, Any], *, include_outcome: bool) -> str:
    """Backward-compatible wrapper — embeddings use memory text only."""
    events = list(metadata.get("events") or metadata.get("calendar_titles") or [])
    if not events and metadata.get("activity"):
        events = [str(metadata["activity"])]
    return build_memory_summary_text(
        events=events,
        locations=list(metadata.get("locations") or []),
        event_categories=list(metadata.get("event_categories") or [metadata.get("category") or "other"]),
        prospective=not include_outcome and metadata.get("kind") == "query",
    )


def build_retrospective_episode(
    *,
    episode_date: date,
    calendar: list[dict[str, Any]] | None = None,
    legacy_calendar_event: str | None = None,
    environment: dict[str, Any] | None = None,
    day_symp: bool = False,
    night_symp: bool = False,
    limit_activity: bool = False,
    puffs_today: int = 0,
    triggers: list[str] | None = None,
    symptoms_next_day: list[str] | None = None,
) -> BuiltEpisode:
    environment = environment or {}
    titles = _calendar_titles(calendar, legacy_calendar_event)
    locations = _locations(calendar)
    categories = _event_categories(titles) if titles else ["other"]
    activity = _primary_activity(titles)
    category = _legacy_category(activity, titles)
    factors = _exposure_factors(
        category=category,
        activity=activity,
        environment=environment,
        triggers=triggers,
    )
    metadata: dict[str, Any] = {
        "activity": activity,
        "category": category,
        "events": titles,
        "locations": locations,
        "event_categories": categories,
        "environment": _environment_payload(environment),
        "exposure_factors": factors,
        "outcome": {
            "symptoms": _symptom_labels(
                day_symp=day_symp,
                night_symp=night_symp,
                limit_activity=limit_activity,
            ),
            "puffs_today": int(puffs_today or 0),
            "symptoms_next_day": list(symptoms_next_day or []),
        },
        "calendar_titles": titles,
    }
    return BuiltEpisode(
        episode_date=episode_date,
        summary_text=build_memory_summary_text(
            events=titles,
            locations=locations,
            event_categories=categories,
            prospective=False,
        ),
        metadata=metadata,
        kind="retrospective",
    )


def build_query_episode(
    *,
    episode_date: date,
    calendar: list[dict[str, Any]] | None = None,
    environment: dict[str, Any] | None = None,
    forecast: dict[str, Any] | None = None,
    question: str | None = None,
) -> BuiltEpisode:
    """Prospective memory query — calendar/life context only (not risk/ML features).

    ``environment`` / ``forecast`` are accepted for API compatibility but are not
    embedded. Risk stays with the ML forecast path.
    """
    _ = environment, forecast  # risk_context — intentionally unused for retrieval
    titles = _calendar_titles(calendar)
    locations = _locations(calendar)
    categories = _event_categories(titles) if titles else ["other"]
    activity = _primary_activity(titles)
    category = _legacy_category(activity, titles)
    # Activity-derived factors only (no pollen/AQI from env).
    factors = _exposure_factors(
        category=category,
        activity=" ".join(titles) or activity,
        environment={},
        triggers=None,
    )
    events_for_text = list(titles)
    q = (question or "").strip()
    if q:
        # Keep free-text question only as optional activity hint, not risk factors.
        events_for_text = [*events_for_text, q]
    metadata: dict[str, Any] = {
        "activity": activity,
        "category": category,
        "events": titles,
        "locations": locations,
        "event_categories": categories,
        "environment": {},
        "exposure_factors": factors,
        "outcome": {},
        "calendar_titles": titles,
        "question": q or None,
        "kind": "query",
    }
    return BuiltEpisode(
        episode_date=episode_date,
        summary_text=build_memory_summary_text(
            events=events_for_text,
            locations=locations,
            event_categories=categories,
            prospective=True,
        ),
        metadata=metadata,
        kind="query",
    )

"""Context providers used by the Copilot recommendation graph."""

from __future__ import annotations

import json
import re
import uuid
from collections import defaultdict
from datetime import date, datetime, timedelta
from pathlib import Path
from typing import Any, Protocol

from sqlalchemy import select
from sqlalchemy.orm import Session

from copilot.state import (
    AdviceType,
    CalendarEvent,
    HistoricalEpisode,
    HistoryContext,
    InsightsContext,
    KnowledgeChunk,
    KnowledgeAudience,
    PersonalInsight,
)
from db.models import CheckIn, EnvSnapshot, User, WearableDaily

KNOWLEDGE_DIR = Path(__file__).resolve().parent.parent / "knowledge"


class CalendarProvider(Protocol):
    """Boundary for calendar context used by the Copilot calendar node."""

    def get_events(self, user_id: uuid.UUID, start: date, end: date) -> list[CalendarEvent]: ...


class NullCalendarProvider:
    """Empty calendar when no Google/manual/request events are available."""

    def get_events(self, user_id: uuid.UUID, start: date, end: date) -> list[CalendarEvent]:
        return []


class ManualCalendarProvider:
    """Legacy free-text calendar_event from a check-in."""

    def __init__(self, calendar_event: str | None, event_date: date):
        title = (calendar_event or "").strip()
        self._events: list[CalendarEvent] = (
            [CalendarEvent(title=title, start=event_date, source="manual")]
            if title
            else []
        )

    def get_events(self, user_id: uuid.UUID, start: date, end: date) -> list[CalendarEvent]:
        return [event for event in self._events if start <= _event_date(event) <= end]


class StructuredCalendarProvider:
    """Production calendar adapter for Google / manual-events / request overrides.

    Accepts the same event dicts produced by ``services.google_calendar`` and
    ``POST /v1/calendar/manual-events``. Events are returned to LangGraph with
    title, times, location, and description so advice can reference real plans.
    """

    def __init__(
        self,
        events: list[CalendarEvent | dict[str, Any]] | None = None,
        *,
        default_source: str = "google_calendar",
        pre_scoped: bool = False,
    ):
        self._pre_scoped = pre_scoped
        self._events = [
            event if isinstance(event, CalendarEvent) else _calendar_event_from_dict(event, default_source)
            for event in (events or [])
        ]

    def get_events(self, user_id: uuid.UUID, start: date, end: date) -> list[CalendarEvent]:
        if self._pre_scoped:
            return list(self._events)
        return [event for event in self._events if _event_overlaps_range(event, start, end)]


class MockCalendarProvider:
    """Deterministic calendar provider for tests and local graph demos."""

    def __init__(self, events: list[CalendarEvent | dict[str, Any]]):
        self._events = [
            event if isinstance(event, CalendarEvent) else CalendarEvent.model_validate(event)
            for event in events
        ]

    def get_events(self, user_id: uuid.UUID, start: date, end: date) -> list[CalendarEvent]:
        return [event for event in self._events if start <= _event_date(event) <= end]


class PreloadedEnvironmentProvider:
    def __init__(self, environment: dict[str, Any]):
        self._environment = environment

    def get_daily(self) -> dict[str, Any]:
        return dict(self._environment)


class ProfileProvider:
    def __init__(self, user: User):
        self._user = user

    def get_profile(self) -> dict[str, Any]:
        return {
            "preferred_environment": self._user.preferred_environment,
            "care_goal": self._user.care_goal,
            "known_triggers": list(self._user.trigger_preferences or []),
            "trigger_sensitivities": dict(self._user.trigger_sensitivities or {}),
        }


def _event_date(event: CalendarEvent) -> date:
    start = event.start
    return start.date() if isinstance(start, datetime) else start


def _parse_event_instant(value: Any) -> datetime | date | None:
    if value is None or value == "":
        return None
    if isinstance(value, datetime):
        return value
    if isinstance(value, date):
        return value
    if isinstance(value, str):
        text = value.strip()
        if not text:
            return None
        if text.endswith("Z"):
            text = text[:-1] + "+00:00"
        try:
            if "T" in text:
                return datetime.fromisoformat(text)
            return date.fromisoformat(text)
        except ValueError:
            return None
    return None


def _calendar_event_from_dict(raw: dict[str, Any], default_source: str) -> CalendarEvent:
    start = _parse_event_instant(raw.get("start")) or date.today()
    end = _parse_event_instant(raw.get("end"))
    title = str(raw.get("title") or raw.get("summary") or "Event").strip() or "Event"
    source = str(raw.get("source") or default_source)
    location = raw.get("location")
    description = raw.get("description")
    return CalendarEvent(
        title=title[:300],
        start=start,
        end=end,
        source=source,
        location=str(location) if location else None,
        description=str(description) if description else None,
        all_day=bool(raw.get("all_day", False)),
    )


def _event_overlaps_range(event: CalendarEvent, start: date, end: date) -> bool:
    event_start = _event_date(event)
    if event.end is None:
        return start <= event_start <= end
    event_end_raw = event.end
    event_end = event_end_raw.date() if isinstance(event_end_raw, datetime) else event_end_raw
    # Inclusive range: event overlaps [start, end] if it starts before end+1 and ends on/after start.
    return event_start <= end and event_end >= start


_SEARCH_STOPWORDS = {
    "asthma",
    "average",
    "elevated",
    "high",
    "increased",
    "level",
    "low",
    "recent",
    "recorded",
    "risk",
    "symptoms",
    "today",
}


def _tokens(value: str) -> set[str]:
    return {
        token
        for token in re.findall(r"[a-z0-9]+", value.lower())
        if len(token) > 2 and token not in _SEARCH_STOPWORDS
    }


class RelevantHistoryProvider:
    """Hybrid episode memory (pgvector + FTS) for the Copilot history node.

    Today's check-in/env still reach the LLM via other nodes. This provider only
    retrieves similar *past* retrospective episodes. Empty memory is fine.
    """

    def __init__(
        self,
        db: Session,
        user_id: uuid.UUID,
        *,
        default_lookback_days: int = 56,
        maximum_lookback_days: int = 365,
        max_examples: int = 5,
        embedder=None,
        use_embeddings: bool = True,
    ):
        self.db = db
        self.user_id = user_id
        self.default_lookback_days = default_lookback_days
        self.maximum_lookback_days = maximum_lookback_days
        self.max_examples = max_examples
        self.embedder = embedder
        self.use_embeddings = use_embeddings

    def get_relevant_history(
        self,
        *,
        anchor_date: date,
        forecast: dict[str, Any],
        calendar: list[dict[str, Any]],
        environment: dict[str, Any],
        question: str | None = None,
        lookback_days: int | None = None,
    ) -> tuple[HistoryContext, list[HistoricalEpisode]]:
        from copilot.episodes import build_query_episode
        from copilot.retrieval import HybridEpisodeRetriever, build_metric_windows

        days = min(max(1, lookback_days or self.default_lookback_days), self.maximum_lookback_days)
        since = anchor_date - timedelta(days=days)
        query = build_query_episode(
            episode_date=anchor_date + timedelta(days=1),
            calendar=calendar,
            environment=environment,
            forecast=forecast,
            question=question,
        )
        retriever = HybridEpisodeRetriever(
            self.db,
            self.user_id,
            embedder=self.embedder,
            default_lookback_days=self.default_lookback_days,
            maximum_lookback_days=self.maximum_lookback_days,
            max_examples=self.max_examples,
            use_embeddings=self.use_embeddings,
        )
        ranked, analysis_pool, window_days = retriever.retrieve(
            query,
            anchor_date=anchor_date,
            lookback_days=days,
        )
        metrics = build_metric_windows(self.db, self.user_id, since=since, before=anchor_date)
        # Keep the compact recent windows PersonalInsights expects.
        for key, series in list(metrics.items()):
            metrics[key] = series[-7:]
            if key == "sleep":
                metrics[key] = [
                    {"date": item["date"], "minutes": item.get("sleep_minutes")}
                    for item in metrics[key]
                ]
            elif key == "symptoms":
                metrics[key] = [
                    {
                        "date": item["date"],
                        "daytime": item.get("daytime"),
                        "nighttime": item.get("nighttime"),
                        "activity_limitation": item.get("limit_activity"),
                    }
                    for item in metrics[key]
                ]
        return (
            HistoryContext(window_days=window_days, episodes=ranked, metric_windows=metrics),
            analysis_pool,
        )


class PersonalInsightsProvider:
    """Compute transparent associations and trends; never infer causality."""

    def compute(
        self,
        history: HistoryContext,
        analysis_pool: list[HistoricalEpisode],
    ) -> InsightsContext:
        patterns: list[PersonalInsight] = []
        event_groups: dict[str, list[HistoricalEpisode]] = defaultdict(list)
        for episode in analysis_pool:
            for event in episode.events:
                event_groups[event.strip().lower()].append(episode)

        for normalized, episodes in event_groups.items():
            if len(episodes) < 2:
                continue
            symptoms_after = sum(
                bool(episode.symptoms_same_day or episode.symptoms_next_day)
                for episode in episodes
            )
            label = episodes[0].events[0]
            patterns.append(
                PersonalInsight(
                    kind="pattern",
                    label=label,
                    statement=(
                        f"{symptoms_after} of {len(episodes)} '{label}' events were followed "
                        "by symptoms on the same or next daily check-in."
                    ),
                    evidence_strength=_evidence_strength(len(episodes)),
                    statistics={
                        "occurrences": len(episodes),
                        "symptoms_within_approx_24h": symptoms_after,
                        "window_days": history.window_days,
                    },
                    supporting_dates=[episode.date for episode in episodes],
                )
            )

        trends: list[PersonalInsight] = []
        symptom_window = history.metric_windows.get("symptoms", [])
        consecutive_nights = 0
        for item in reversed(symptom_window):
            if item.get("nighttime"):
                consecutive_nights += 1
            else:
                break
        if consecutive_nights >= 2:
            trends.append(
                PersonalInsight(
                    kind="trend",
                    label="Recent nighttime symptoms",
                    statement=f"Nighttime symptoms were logged for {consecutive_nights} consecutive days.",
                    evidence_strength=_evidence_strength(consecutive_nights),
                    statistics={"consecutive_days": consecutive_nights},
                )
            )

        statistics: list[PersonalInsight] = []
        puff_values = [int(item.get("puffs") or 0) for item in history.metric_windows.get("rescue_inhaler", [])]
        if puff_values:
            statistics.append(
                PersonalInsight(
                    kind="statistic",
                    label="Recent rescue inhaler use",
                    statement=f"{sum(puff_values)} rescue puffs were logged across {len(puff_values)} recent days.",
                    evidence_strength=_evidence_strength(len(puff_values)),
                    statistics={
                        "total_puffs": sum(puff_values),
                        "days_observed": len(puff_values),
                        "daily_average": round(sum(puff_values) / len(puff_values), 2),
                    },
                )
            )

        sleep_values = [
            int(item["minutes"])
            for item in history.metric_windows.get("sleep", [])
            if item.get("minutes") is not None
        ]
        if sleep_values:
            statistics.append(
                PersonalInsight(
                    kind="statistic",
                    label="Recent sleep",
                    statement=f"Average recorded sleep was {round(sum(sleep_values) / len(sleep_values))} minutes.",
                    evidence_strength=_evidence_strength(len(sleep_values)),
                    statistics={
                        "average_minutes": round(sum(sleep_values) / len(sleep_values)),
                        "days_observed": len(sleep_values),
                    },
                )
            )

        return InsightsContext(patterns=patterns, trends=trends, statistics=statistics)


def _evidence_strength(occurrences: int) -> str:
    if occurrences >= 8:
        return "high"
    if occurrences >= 5:
        return "moderate"
    if occurrences >= 3:
        return "low"
    return "insufficient"


class MedicalKnowledgeProvider:
    """Small JSON retriever with a contract that can later back onto embeddings."""

    def __init__(self, knowledge_dir: Path = KNOWLEDGE_DIR):
        self.knowledge_dir = knowledge_dir

    def search(
        self,
        query_terms: list[str],
        limit: int = 4,
        *,
        advice_type: AdviceType = "daily",
        audience: KnowledgeAudience = "patient",
    ) -> list[KnowledgeChunk]:
        chunks = [
            chunk
            for chunk in self._load()
            if chunk.audience == audience
            and (advice_type == "daily" or advice_type in chunk.advice_types)
        ]
        if not chunks:
            return []

        term_tokens = [_tokens(term) for term in query_terms]
        term_tokens = [tokens for tokens in term_tokens if tokens]
        if not term_tokens:
            return []
        scored: list[tuple[int, KnowledgeChunk]] = []
        for chunk in chunks:
            tag_tokens = _tokens(" ".join(chunk.tags))
            heading_tokens = _tokens(f"{chunk.title} {chunk.section or ''}")
            body_tokens = _tokens(chunk.body)
            score = sum(
                5 * len(tokens & tag_tokens)
                + 3 * len(tokens & heading_tokens)
                + len(tokens & body_tokens)
                for tokens in term_tokens
            )
            scored.append((score, chunk))
        scored.sort(key=lambda item: item[0], reverse=True)
        return [chunk for score, chunk in scored if score >= 3][:limit]

    def _load(self) -> list[KnowledgeChunk]:
        chunks: list[KnowledgeChunk] = []
        generated = self.knowledge_dir / "generated" / "chunks.json"
        paths = (
            (generated,)
            if generated.exists()
            else (
                self.knowledge_dir / "chunks.json",
                self.knowledge_dir / "layer1.json",
                self.knowledge_dir / "layer2.json",
            )
        )
        for path in paths:
            if not path.exists():
                continue
            for index, raw in enumerate(json.loads(path.read_text())):
                chunks.append(
                    KnowledgeChunk(
                        chunk_id=str(raw.get("chunk_id") or f"{path.stem}:{index}"),
                        title=raw["title"],
                        body=raw["body"],
                        publisher=str(raw.get("publisher") or "local"),
                        source_url=raw.get("source_url"),
                        section=raw.get("section"),
                        tags=list(raw.get("tags", [])),
                        audience=raw.get("audience", "patient"),
                        medication_change_allowed=bool(
                            raw.get("medication_change_allowed", False)
                        ),
                        advice_types=list(raw.get("advice_types", ["daily"])),
                    )
                )
        return chunks

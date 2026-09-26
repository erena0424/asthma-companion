"""Tests for calendar, relevant-history, and personal-insight providers."""

from __future__ import annotations

import json
import uuid
from datetime import date, datetime, timedelta

from sqlalchemy.orm import Session

from copilot.providers import (
    ManualCalendarProvider,
    MedicalKnowledgeProvider,
    MockCalendarProvider,
    PersonalInsightsProvider,
    RelevantHistoryProvider,
    StructuredCalendarProvider,
)
from copilot.state import CalendarEvent
from db.models import CheckIn, EnvSnapshot, User, WearableDaily


def test_manual_calendar_provider_uses_check_in_text():
    provider = ManualCalendarProvider("Outdoor soccer", date(2026, 7, 17))
    events = provider.get_events(uuid.uuid4(), date(2026, 7, 17), date(2026, 7, 17))
    assert len(events) == 1
    assert events[0].title == "Outdoor soccer"
    assert events[0].source == "manual"
    assert ManualCalendarProvider("  ", date(2026, 7, 17)).get_events(
        uuid.uuid4(), date(2026, 7, 17), date(2026, 7, 17)
    ) == []


def test_structured_calendar_provider_preserves_google_fields():
    provider = StructuredCalendarProvider(
        [
            {
                "title": "Outdoor soccer",
                "start": "2026-07-18T09:00:00-05:00",
                "end": "2026-07-18T10:30:00-05:00",
                "location": "Madison park",
                "description": "Scrimmage",
                "all_day": False,
            }
        ],
        default_source="google_calendar",
        pre_scoped=True,
    )
    events = provider.get_events(uuid.uuid4(), date(2026, 7, 17), date(2026, 7, 17))
    assert len(events) == 1
    assert events[0].title == "Outdoor soccer"
    assert events[0].location == "Madison park"
    assert events[0].description == "Scrimmage"
    assert events[0].source == "google_calendar"
    assert events[0].start.date() == date(2026, 7, 18)


def test_medical_knowledge_filters_by_audience_and_advice_type(tmp_path):
    (tmp_path / "chunks.json").write_text(
        json.dumps(
            [
                {
                    "chunk_id": "patient-emergency",
                    "title": "Emergency Signs",
                    "body": "Asthma emergency warning signs.",
                    "publisher": "CDC",
                    "audience": "patient",
                    "medication_change_allowed": False,
                    "advice_types": ["emergency"],
                    "tags": ["asthma"],
                },
                {
                    "chunk_id": "patient-exercise",
                    "title": "Exercise",
                    "body": "Patient exercise precautions.",
                    "publisher": "CDC",
                    "audience": "patient",
                    "medication_change_allowed": False,
                    "advice_types": ["exercise"],
                    "tags": ["asthma"],
                },
                {
                    "chunk_id": "clinician-treatment",
                    "title": "Clinical Treatment",
                    "body": "Clinical treatment guidance.",
                    "publisher": "NHLBI",
                    "audience": "clinician",
                    "medication_change_allowed": False,
                    "advice_types": ["clinical_reference"],
                    "tags": ["asthma"],
                },
            ]
        )
    )
    provider = MedicalKnowledgeProvider(tmp_path)

    emergency = provider.search(
        ["emergency warning signs"],
        advice_type="emergency",
        audience="patient",
    )
    clinical = provider.search(
        ["clinical treatment"],
        advice_type="clinical_reference",
        audience="clinician",
    )
    daily_exercise = provider.search(
        ["anticipated exercise trigger"],
        advice_type="daily",
        audience="patient",
    )
    no_match = provider.search(
        ["unrelated calendar meeting"],
        advice_type="daily",
        audience="patient",
    )

    assert [chunk.chunk_id for chunk in emergency] == ["patient-emergency"]
    assert [chunk.chunk_id for chunk in clinical] == ["clinician-treatment"]
    assert [chunk.chunk_id for chunk in daily_exercise] == ["patient-exercise"]
    assert no_match == []
    assert all(chunk.medication_change_allowed is False for chunk in emergency + clinical)


def test_generated_authoritative_corpus_replaces_legacy_layers(tmp_path):
    (tmp_path / "generated").mkdir()
    authoritative = {
        "chunk_id": "official-pollen",
        "title": "Pollen precautions",
        "body": "Pollen exposure precautions from an authoritative patient source.",
        "publisher": "CDC",
        "audience": "patient",
        "medication_change_allowed": False,
        "advice_types": ["daily"],
        "tags": ["pollen"],
    }
    legacy = {
        **authoritative,
        "chunk_id": "legacy-pollen",
        "publisher": "local",
    }
    (tmp_path / "generated" / "chunks.json").write_text(json.dumps([authoritative]))
    (tmp_path / "layer1.json").write_text(json.dumps([legacy]))

    results = MedicalKnowledgeProvider(tmp_path).search(
        ["high pollen"],
        advice_type="daily",
        audience="patient",
    )

    assert [chunk.chunk_id for chunk in results] == ["official-pollen"]


def test_mock_calendar_provider_filters_requested_dates():
    provider = MockCalendarProvider(
        [
            CalendarEvent(title="Friday Meeting", start=datetime(2026, 1, 30, 9)),
            CalendarEvent(title="Saturday Run", start=datetime(2026, 1, 31, 8)),
        ]
    )

    events = provider.get_events(uuid.uuid4(), date(2026, 1, 30), date(2026, 1, 30))

    assert [event.title for event in events] == ["Friday Meeting"]


def test_relevant_history_and_insights_use_backend_counts(db_session: Session):
    from copilot.embeddings import StubEmbedder
    from services.episode_store import upsert_retrospective_from_day

    user = User(email="history@example.com", password_hash="test")
    db_session.add(user)
    db_session.flush()
    embedder = StubEmbedder()

    anchor = date(2026, 1, 30)
    meeting_dates = [date(2026, 1, 2), date(2026, 1, 9), date(2026, 1, 16), date(2026, 1, 23)]
    for index, day in enumerate(meeting_dates):
        db_session.add(
            CheckIn(
                user_id=user.id,
                date=day,
                calendar_event="Friday Meeting",
                calendar_events=[{"title": "Friday Meeting", "start": day.isoformat()}],
                daily_day_symp=index < 3,
                daily_night_symp=False,
                daily_limit_activity=False,
                symptoms_logged=True,
                puffs_today=1 if index < 3 else 0,
                triggers=["pollen"] if index < 3 else [],
            )
        )
        db_session.add(
            WearableDaily(
                user_id=user.id,
                date=day - timedelta(days=1),
                sleep_minutes=300 + index * 30,
            )
        )
        db_session.add(
            EnvSnapshot(
                user_id=user.id,
                date=day,
                lat=42.36,
                lon=-71.06,
                provider="test",
                features={"aqi": 4 if index < 3 else 1, "tree_pollen": "High"},
                missing=[],
            )
        )
        upsert_retrospective_from_day(db_session, user.id, day, embedder=embedder)
    db_session.flush()

    provider = RelevantHistoryProvider(db_session, user.id, max_examples=3, embedder=embedder)
    history, analysis_pool = provider.get_relevant_history(
        anchor_date=anchor,
        forecast={"contributing_factors": ["Elevated air quality index"]},
        calendar=[{"title": "Friday Meeting"}],
        environment={"aqi": 4, "tree_pollen": "High"},
    )

    assert history.window_days == 56
    assert len(history.episodes) >= 1
    assert len(analysis_pool) >= 1
    assert any("Friday Meeting" in episode.events for episode in history.episodes)
    assert history.metric_windows["sleep"]

    insights = PersonalInsightsProvider().compute(history, analysis_pool)
    meeting = next(item for item in insights.patterns if item.label == "Friday Meeting")
    assert meeting.statistics["occurrences"] == 4
    assert meeting.statistics["symptoms_within_approx_24h"] == 3
    assert meeting.evidence_strength == "low"
    assert "3 of 4" in meeting.statement

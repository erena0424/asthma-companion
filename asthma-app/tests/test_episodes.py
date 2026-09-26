"""Tests for episode builder, stub embeddings, hybrid retrieval, and store."""

from __future__ import annotations

import math
from datetime import date, timedelta

from sqlalchemy.orm import Session

from copilot.embeddings import StubEmbedder
from copilot.episodes import build_memory_summary_text, build_query_episode, build_retrospective_episode
from copilot.providers import PersonalInsightsProvider, RelevantHistoryProvider
from copilot.retrieval import HybridEpisodeRetriever, fuse_scores
from db.models import CheckIn, EnvSnapshot, User, WearableDaily
from services.episode_store import upsert_built_episode, upsert_retrospective_from_day


def _cosine(a: list[float], b: list[float]) -> float:
    return sum(x * y for x, y in zip(a, b))


def test_episode_builder_memory_text_excludes_risk_env():
    built = build_retrospective_episode(
        episode_date=date(2026, 7, 16),
        calendar=[{"title": "Outdoor soccer (club pickup)", "location": "Campus field"}],
        environment={"temperature": 42, "tree_pollen": "High", "aqi": 3},
        day_symp=True,
        puffs_today=2,
    )
    assert built.metadata["category"] == "outdoor_exercise"
    assert "high_pollen" in built.metadata["exposure_factors"]
    assert built.metadata["environment"]["pollen"] == "high"
    # Embedding key is life situation — not a second risk model.
    assert "pollen" not in built.summary_text.lower()
    assert "aqi" not in built.summary_text.lower()
    assert "rescue" not in built.summary_text.lower()
    assert "Outdoor soccer" in built.summary_text
    assert "Campus field" in built.summary_text
    assert "pef" not in built.summary_text.lower()


def test_query_episode_ignores_forecast_risk_factors():
    query = build_query_episode(
        episode_date=date(2026, 7, 29),
        calendar=[
            {"title": "BIO 201 — Lecture", "location": "Science Hall 214"},
            {"title": "Gym — cardio + weights", "location": "Campus Rec Center"},
        ],
        environment={"tree_pollen": "High", "aqi": 4},
        forecast={"contributing_factors": ["High pollen", "Exercise"]},
    )
    assert "pollen" not in query.summary_text.lower()
    assert "exercise" not in query.summary_text.lower() or "physical activity" in query.summary_text.lower()
    # "Exercise" as ML factor must not be injected; gym still yields indoor physical activity.
    assert "High pollen" not in query.summary_text
    assert "BIO 201" in query.summary_text
    assert "Gym" in query.summary_text
    assert "Science Hall" in query.summary_text
    assert query.metadata.get("environment") == {}


def test_stub_embedder_lecture_closer_than_soccer_for_class_query():
    embedder = StubEmbedder()
    query = embedder.embed(
        build_memory_summary_text(
            events=["BIO 201 — Lecture", "BIO 201 — Lab"],
            locations=["Science Hall"],
            event_categories=["lecture", "lab"],
            prospective=True,
        )
    )
    lecture = embedder.embed(
        build_memory_summary_text(
            events=["STAT 120 — Lecture"],
            locations=["Social Sciences 101"],
            event_categories=["lecture"],
            prospective=False,
        )
    )
    soccer = embedder.embed(
        build_memory_summary_text(
            events=["Outdoor soccer (club pickup)"],
            locations=["Campus field"],
            event_categories=["outdoor_exercise"],
            prospective=False,
        )
    )
    assert _cosine(query, lecture) > _cosine(query, soccer)


def test_fuse_scores_prefers_keyword_exact_match():
    import uuid

    a, b, c = uuid.uuid4(), uuid.uuid4(), uuid.uuid4()
    # STAT exact keyword should beat higher pure vector CS lecture when fused.
    fused = fuse_scores(
        vector_scores={a: 0.7, b: 0.8, c: 0.5},
        keyword_scores={a: 1.0, b: 0.0, c: 0.0},
        recency_scores={a: 0.5, b: 0.5, c: 0.5},
    )
    assert fused[a] > fused[b]


def test_hybrid_retrieval_prefers_lecture_over_outdoor_for_class_day(db_session: Session):
    user = User(email="memory-boundary@example.com", password_hash="test")
    db_session.add(user)
    db_session.flush()
    embedder = StubEmbedder()
    anchor = date(2026, 7, 28)

    samples = [
        (date(2026, 7, 14), "Outdoor soccer (club pickup)", "Campus field", True, 2, {"tree_pollen": "High", "aqi": 3}),
        (date(2026, 7, 21), "STAT 120 — Lecture", "Social Sciences 101", False, 0, {"tree_pollen": "Low", "aqi": 1}),
        (date(2026, 7, 7), "BIO 201 — Lecture", "Science Hall 214", False, 0, {"tree_pollen": "Low", "aqi": 1}),
    ]
    for day, title, location, day_symp, puffs, env in samples:
        db_session.add(
            CheckIn(
                user_id=user.id,
                date=day,
                calendar_event=title,
                calendar_events=[{"title": title, "location": location, "start": day.isoformat()}],
                daily_day_symp=day_symp,
                symptoms_logged=True,
                puffs_today=puffs,
            )
        )
        db_session.add(
            EnvSnapshot(
                user_id=user.id,
                date=day,
                lat=42.36,
                lon=-71.06,
                provider="test",
                features=env,
                missing=[],
            )
        )
        upsert_retrospective_from_day(db_session, user.id, day, embedder=embedder)
    db_session.flush()

    provider = RelevantHistoryProvider(db_session, user.id, max_examples=3, embedder=embedder)
    history, _pool = provider.get_relevant_history(
        anchor_date=anchor,
        forecast={"contributing_factors": ["High pollen", "Exercise"]},  # must not dominate retrieval
        calendar=[
            {"title": "BIO 201 — Lecture", "location": "Science Hall 214"},
            {"title": "BIO 201 — Lab", "location": "Science Hall Lab B"},
            {"title": "Gym — cardio + weights", "location": "Campus Rec Center"},
        ],
        environment={"aqi": 4, "tree_pollen": "High"},
    )
    assert history.episodes
    top_titles = " ".join(" ".join(ep.events) for ep in history.episodes[:2]).lower()
    assert "lecture" in top_titles or "bio" in top_titles or "stat" in top_titles
    assert "soccer" not in " ".join(history.episodes[0].events).lower()


def test_relevant_history_and_insights_use_backend_counts(db_session: Session):
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
    assert any("Friday Meeting" in episode.events for episode in history.episodes)
    assert history.metric_windows["sleep"]

    insights = PersonalInsightsProvider().compute(history, analysis_pool)
    meeting = next(item for item in insights.patterns if item.label == "Friday Meeting")
    assert meeting.statistics["occurrences"] == 4


def test_upsert_stores_embedding(db_session: Session):
    user = User(email="embed-store@example.com", password_hash="test")
    db_session.add(user)
    db_session.flush()
    built = build_retrospective_episode(
        episode_date=date(2026, 7, 1),
        calendar=[{"title": "STAT 120 — Lecture"}],
        environment={"aqi": 2},
        night_symp=True,
        puffs_today=0,
    )
    row = upsert_built_episode(db_session, user.id, built, embedder=StubEmbedder())
    assert row is not None
    assert row.embedding is not None
    assert len(row.embedding) == 768
    assert math.isclose(sum(x * x for x in row.embedding), 1.0, rel_tol=1e-5)
    assert "pollen" not in row.summary_text.lower()


def test_retrieve_skips_embedder_when_disabled(db_session: Session, monkeypatch):
    user = User(email="no-embed@example.com", password_hash="test")
    db_session.add(user)
    db_session.flush()

    def _boom(*_args, **_kwargs):
        raise AssertionError("get_embedder should not run when use_embeddings=False")

    monkeypatch.setattr("copilot.retrieval.get_embedder", _boom)
    query = build_query_episode(
        episode_date=date(2026, 7, 2),
        calendar=[{"title": "Walk outdoors"}],
        environment={"aqi": 2},
        forecast={"risk_level": "Low", "contributing_factors": []},
        question="Can I go for a walk?",
    )
    retriever = HybridEpisodeRetriever(db_session, user.id, use_embeddings=False)
    ranked, _pool, _days = retriever.retrieve(query, anchor_date=date(2026, 7, 1))
    assert isinstance(ranked, list)

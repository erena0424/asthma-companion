"""Persist retrospective asthma episodes (embed + FTS) without blocking forecasts."""

from __future__ import annotations

import logging
import uuid
from datetime import date, timedelta
from typing import Any

from sqlalchemy import select, text
from sqlalchemy.orm import Session

from copilot.embeddings import Embedder, get_embedder
from copilot.episodes import BuiltEpisode, build_retrospective_episode
from db.models import CheckIn, Episode, EnvSnapshot

logger = logging.getLogger(__name__)


def _symptoms_list(check_in: CheckIn | None) -> list[str]:
    if check_in is None:
        return []
    labels: list[str] = []
    if check_in.daily_day_symp:
        labels.append("daytime symptoms")
    if check_in.daily_night_symp:
        labels.append("nighttime symptoms")
    if check_in.daily_limit_activity:
        labels.append("activity limitation")
    return labels


def upsert_built_episode(
    db: Session,
    user_id: uuid.UUID,
    built: BuiltEpisode,
    *,
    embedder: Embedder | None = None,
    skip_embed: bool = False,
) -> Episode | None:
    """Insert/update a retrospective episode. Embedding failure stores NULL vector."""
    if built.kind != "retrospective":
        return None

    row = db.scalar(
        select(Episode).where(Episode.user_id == user_id, Episode.episode_date == built.episode_date)
    )
    if row is None:
        row = Episode(
            user_id=user_id,
            episode_date=built.episode_date,
            kind="retrospective",
            summary_text=built.summary_text,
            metadata_=built.metadata,
        )
        db.add(row)
    else:
        row.kind = "retrospective"
        row.summary_text = built.summary_text
        row.metadata_ = built.metadata

    embedding: list[float] | None = None
    if not skip_embed:
        try:
            embedding = (embedder or get_embedder()).embed(built.summary_text)
        except Exception as exc:
            logger.warning(
                "Episode embed failed for user=%s date=%s: %s",
                user_id,
                built.episode_date,
                exc,
            )
    row.embedding = embedding
    db.flush()
    db.execute(
        text(
            "UPDATE episodes SET search_tsv = to_tsvector('english', summary_text) "
            "WHERE id = :id"
        ),
        {"id": row.id},
    )
    db.flush()
    return row


def upsert_retrospective_from_day(
    db: Session,
    user_id: uuid.UUID,
    day: date,
    *,
    environment: dict[str, Any] | None = None,
    embedder: Embedder | None = None,
    skip_embed: bool = False,
) -> Episode | None:
    """Build + store episode for a resolved day (check-in preferred; env optional)."""
    # Ensure pending check-ins/env rows in this session are queryable (autoflush=False).
    db.flush()
    check_in = db.scalar(select(CheckIn).where(CheckIn.user_id == user_id, CheckIn.date == day))
    if check_in is None:
        return None

    env = environment
    if env is None:
        snapshot = db.scalar(
            select(EnvSnapshot).where(EnvSnapshot.user_id == user_id, EnvSnapshot.date == day)
        )
        env = dict(snapshot.features or {}) if snapshot else {}

    next_check_in = db.scalar(
        select(CheckIn).where(CheckIn.user_id == user_id, CheckIn.date == day + timedelta(days=1))
    )
    built = build_retrospective_episode(
        episode_date=day,
        calendar=list(check_in.calendar_events or []),
        legacy_calendar_event=check_in.calendar_event,
        environment=env,
        day_symp=bool(check_in.daily_day_symp),
        night_symp=bool(check_in.daily_night_symp),
        limit_activity=bool(check_in.daily_limit_activity),
        puffs_today=int(check_in.puffs_today or 0),
        triggers=list(check_in.triggers or []),
        symptoms_next_day=_symptoms_list(next_check_in),
    )
    return upsert_built_episode(
        db, user_id, built, embedder=embedder, skip_embed=skip_embed
    )


def soft_upsert_episode_for_forecast(
    db: Session,
    user_id: uuid.UUID,
    day: date,
    *,
    environment: dict[str, Any] | None = None,
    embedder: Embedder | None = None,
    skip_embed: bool = True,
) -> None:
    """Best-effort retrospective upsert; never raises to the forecast caller.

    Embedding is skipped on the forecast hot path by default so a slow/broken
    Gemini embedding model cannot freeze the API worker.
    """
    try:
        upsert_retrospective_from_day(
            db,
            user_id,
            day,
            environment=environment,
            embedder=embedder,
            skip_embed=skip_embed,
        )
        # Refresh yesterday with next-day symptom linkage when available.
        yesterday = day - timedelta(days=1)
        if db.scalar(select(CheckIn).where(CheckIn.user_id == user_id, CheckIn.date == yesterday)):
            upsert_retrospective_from_day(
                db, user_id, yesterday, embedder=embedder, skip_embed=skip_embed
            )
    except Exception:
        logger.exception("Failed to upsert retrospective episode for user=%s day=%s", user_id, day)

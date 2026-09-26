"""Hybrid episode retrieval: pgvector similarity + Postgres full-text search."""

from __future__ import annotations

import uuid
from datetime import date, timedelta
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from copilot.embeddings import Embedder, get_embedder
from copilot.episodes import BuiltEpisode
from copilot.state import HistoricalEpisode
from db.models import CheckIn, Episode, WearableDaily


def _normalize_rank_map(scores: dict[uuid.UUID, float]) -> dict[uuid.UUID, float]:
    if not scores:
        return {}
    lo = min(scores.values())
    hi = max(scores.values())
    if hi <= lo:
        return {key: 1.0 for key in scores}
    return {key: (value - lo) / (hi - lo) for key, value in scores.items()}


def fuse_scores(
    *,
    vector_scores: dict[uuid.UUID, float],
    keyword_scores: dict[uuid.UUID, float],
    recency_scores: dict[uuid.UUID, float],
    semantic_weight: float = 0.5,
    keyword_weight: float = 0.3,
    recency_weight: float = 0.2,
) -> dict[uuid.UUID, float]:
    """Weighted fusion after per-channel min-max normalization.

    Defaults bias toward life-situation similarity + exact personal patterns,
    with a meaningful recency prior (not a second risk model).
    """
    v = _normalize_rank_map(vector_scores)
    k = _normalize_rank_map(keyword_scores)
    r = _normalize_rank_map(recency_scores)
    ids = set(v) | set(k) | set(r)
    fused: dict[uuid.UUID, float] = {}
    for episode_id in ids:
        fused[episode_id] = (
            semantic_weight * v.get(episode_id, 0.0)
            + keyword_weight * k.get(episode_id, 0.0)
            + recency_weight * r.get(episode_id, 0.0)
        )
    return fused


class HybridEpisodeRetriever:
    def __init__(
        self,
        db: Session,
        user_id: uuid.UUID,
        *,
        embedder: Embedder | None = None,
        default_lookback_days: int = 56,
        maximum_lookback_days: int = 365,
        max_examples: int = 5,
        analysis_pool_size: int = 30,
        candidate_limit: int = 20,
        use_embeddings: bool = True,
    ):
        self.db = db
        self.user_id = user_id
        self.embedder = embedder
        self.default_lookback_days = default_lookback_days
        self.maximum_lookback_days = maximum_lookback_days
        self.max_examples = max_examples
        self.analysis_pool_size = analysis_pool_size
        self.candidate_limit = candidate_limit
        self.use_embeddings = use_embeddings

    def _lookback(self, lookback_days: int | None) -> int:
        return min(max(1, lookback_days or self.default_lookback_days), self.maximum_lookback_days)

    def _vector_candidates(
        self,
        *,
        query_embedding: list[float] | None,
        since: date,
        before: date,
    ) -> dict[uuid.UUID, float]:
        if not query_embedding:
            return {}
        distance = Episode.embedding.cosine_distance(query_embedding)
        rows = self.db.execute(
            select(Episode.id, distance.label("distance"))
            .where(
                Episode.user_id == self.user_id,
                Episode.episode_date >= since,
                Episode.episode_date < before,
                Episode.embedding.is_not(None),
            )
            .order_by(distance)
            .limit(self.candidate_limit)
        ).all()
        scores: dict[uuid.UUID, float] = {}
        for episode_id, dist in rows:
            scores[episode_id] = 1.0 / (1.0 + float(dist or 0.0))
        return scores

    def _keyword_candidates(
        self,
        *,
        query_text: str,
        since: date,
        before: date,
    ) -> dict[uuid.UUID, float]:
        cleaned = (query_text or "").strip()
        if not cleaned:
            return {}
        tsq = func.plainto_tsquery("english", cleaned)
        rank = func.ts_rank_cd(Episode.search_tsv, tsq)
        rows = self.db.execute(
            select(Episode.id, rank.label("rank"))
            .where(
                Episode.user_id == self.user_id,
                Episode.episode_date >= since,
                Episode.episode_date < before,
                Episode.search_tsv.is_not(None),
                Episode.search_tsv.op("@@")(tsq),
            )
            .order_by(rank.desc())
            .limit(self.candidate_limit)
        ).all()
        return {episode_id: float(score or 0.0) for episode_id, score in rows}

    def retrieve(
        self,
        query: BuiltEpisode,
        *,
        anchor_date: date,
        lookback_days: int | None = None,
        warnings: list[str] | None = None,
    ) -> tuple[list[HistoricalEpisode], list[HistoricalEpisode], int]:
        days = self._lookback(lookback_days)
        since = anchor_date - timedelta(days=days)
        before = anchor_date

        warn_out = warnings if warnings is not None else []
        query_embedding: list[float] | None = None
        if self.use_embeddings:
            try:
                embedder = self.embedder or get_embedder()
                query_embedding = embedder.embed(query.summary_text)
            except Exception:
                warn_out.append(
                    "Episode embedding unavailable; using keyword-only memory retrieval."
                )

        vector_scores = self._vector_candidates(
            query_embedding=query_embedding,
            since=since,
            before=before,
        )
        keyword_scores = self._keyword_candidates(
            query_text=query.summary_text,
            since=since,
            before=before,
        )

        if not vector_scores and not keyword_scores:
            rows = list(
                self.db.scalars(
                    select(Episode)
                    .where(
                        Episode.user_id == self.user_id,
                        Episode.episode_date >= since,
                        Episode.episode_date < before,
                    )
                    .order_by(Episode.episode_date.desc())
                    .limit(self.analysis_pool_size)
                ).all()
            )
            mapped = [self._to_historical(row, matched_on=["recency"], score=0.1) for row in rows]
            return mapped[: self.max_examples], mapped, days

        episode_ids = set(vector_scores) | set(keyword_scores)
        episodes = {
            row.id: row
            for row in self.db.scalars(select(Episode).where(Episode.id.in_(episode_ids))).all()
        }
        recency_scores = {
            episode_id: max(
                0.0,
                1.0 - ((anchor_date - episodes[episode_id].episode_date).days / days),
            )
            for episode_id in episode_ids
            if episode_id in episodes
        }
        fused = fuse_scores(
            vector_scores=vector_scores,
            keyword_scores=keyword_scores,
            recency_scores=recency_scores,
        )
        ranked_ids = sorted(fused.keys(), key=lambda eid: fused[eid], reverse=True)
        mapped: list[HistoricalEpisode] = []
        for episode_id in ranked_ids:
            row = episodes.get(episode_id)
            if row is None:
                continue
            matched_on: list[str] = []
            if episode_id in vector_scores:
                matched_on.append("semantic")
            if episode_id in keyword_scores:
                matched_on.append("keyword")
            mapped.append(self._to_historical(row, matched_on=matched_on, score=fused[episode_id]))

        return mapped[: self.max_examples], mapped[: self.analysis_pool_size], days

    @staticmethod
    def _to_historical(
        row: Episode,
        *,
        matched_on: list[str],
        score: float,
    ) -> HistoricalEpisode:
        meta = row.metadata_ or {}
        outcome = meta.get("outcome") or {}
        titles = list(meta.get("events") or meta.get("calendar_titles") or [])
        activity = meta.get("activity")
        if activity and activity not in titles:
            titles = [activity, *titles]
        return HistoricalEpisode(
            date=row.episode_date,
            events=titles,
            environment=dict(meta.get("environment") or {}),
            sleep_minutes=None,
            symptoms_same_day=list(outcome.get("symptoms") or []),
            symptoms_next_day=list(outcome.get("symptoms_next_day") or []),
            puffs_today=int(outcome.get("puffs_today") or 0),
            triggers=list(meta.get("exposure_factors") or []),
            matched_on=matched_on,
            relevance_score=round(float(score), 3),
        )


def build_metric_windows(
    db: Session,
    user_id: uuid.UUID,
    *,
    since: date,
    before: date,
) -> dict[str, list[dict[str, Any]]]:
    """Compact metric series for insights (sourced from check-ins/wearables)."""
    check_ins = list(
        db.scalars(
            select(CheckIn)
            .where(CheckIn.user_id == user_id, CheckIn.date >= since, CheckIn.date < before)
            .order_by(CheckIn.date.asc())
        ).all()
    )
    wearables = {
        row.date: row
        for row in db.scalars(
            select(WearableDaily).where(
                WearableDaily.user_id == user_id,
                WearableDaily.date >= since - timedelta(days=1),
                WearableDaily.date < before,
            )
        ).all()
    }
    sleep_series: list[dict[str, Any]] = []
    for row in check_ins:
        lag = wearables.get(row.date - timedelta(days=1))
        sleep_series.append(
            {
                "date": row.date.isoformat(),
                "sleep_minutes": lag.sleep_minutes if lag else None,
            }
        )
    return {
        "symptoms": [
            {
                "date": row.date.isoformat(),
                "daytime": bool(row.daily_day_symp),
                "nighttime": bool(row.daily_night_symp),
                "limit_activity": bool(row.daily_limit_activity),
            }
            for row in check_ins
        ],
        "rescue_inhaler": [
            {"date": row.date.isoformat(), "puffs": row.puffs_today} for row in check_ins
        ],
        "sleep": sleep_series,
    }

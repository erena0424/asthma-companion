"""Layer 3 — personalized episode pattern summaries from user history."""

from __future__ import annotations

import uuid
from datetime import date, timedelta

from sqlalchemy import select
from sqlalchemy.orm import Session

from db.models import CheckIn, WearableDaily


def _pollen_high(features: dict) -> bool:
    levels = [features.get("tree_pollen"), features.get("grass_pollen"), features.get("weed_pollen")]
    return any(v in ("High", "Very High") for v in levels)


def build_episode_summary(
    db: Session,
    user_id: uuid.UUID,
    *,
    anchor_date: date,
    contributing_factors: list[str],
    lookback_days: int = 365,
) -> str:
    """Summarize recurring patterns from stored check-ins and wearables."""
    since = anchor_date - timedelta(days=lookback_days)
    check_ins = db.scalars(
        select(CheckIn)
        .where(CheckIn.user_id == user_id, CheckIn.date >= since, CheckIn.date <= anchor_date)
        .order_by(CheckIn.date.desc())
    ).all()

    if not check_ins:
        return (
            "[Document 3: Personalized Patient History]\n"
            "Source: Internal Risk Engine & User Logs\n"
            "No prior check-in history yet. Advice will rely on general guidelines and today's inputs."
        )

    high_pollen_days = 0
    poor_sleep_days = 0
    rescue_spike_days = 0
    night_symptom_days = 0
    matched_episodes = 0

    wearables = {
        w.date: w
        for w in db.scalars(
            select(WearableDaily).where(
                WearableDaily.user_id == user_id,
                WearableDaily.date >= since,
                WearableDaily.date <= anchor_date,
            )
        ).all()
    }

    for row in check_ins:
        if row.daily_night_symp:
            night_symptom_days += 1
        if row.puffs_today >= 2:
            rescue_spike_days += 1
        wearable = wearables.get(row.date - timedelta(days=1))
        if wearable and wearable.sleep_minutes is not None and wearable.sleep_minutes < 360:
            poor_sleep_days += 1
        if any(t.lower() in ("pollen", "exercise", "cold air") for t in (row.triggers or [])):
            high_pollen_days += 1
        if row.puffs_today >= 2 and row.daily_night_symp:
            matched_episodes += 1

    factor_text = ", ".join(contributing_factors) if contributing_factors else "current risk signals"
    lines = [
        "[Document 3: Personalized Patient History]",
        "Source: Internal Risk Engine & User Logs",
        f"Over the last {lookback_days} days you logged {len(check_ins)} check-ins.",
        f"Night symptoms on {night_symptom_days} days; rescue inhaler use ≥2 puffs on {rescue_spike_days} days.",
        f"Days with poor sleep (<6h): {poor_sleep_days}.",
        f"Days where triggers included pollen/exercise/cold air: {high_pollen_days}.",
    ]
    if matched_episodes:
        lines.append(
            f"{matched_episodes} prior days combined elevated rescue use with night symptoms — "
            f"similar to today's pattern ({factor_text})."
        )
    else:
        lines.append(f"Today's contributing factors ({factor_text}) are being compared against your growing history.")

    return "\n".join(lines)

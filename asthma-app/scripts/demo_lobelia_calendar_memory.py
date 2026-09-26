#!/usr/bin/env python3
"""End-to-end Lobelia demo: Google Calendar + episode memory + debug output.

Uses a real Mirror Lake user (must already be registered and Google-connected).
Optionally seeds a few past outdoor episodes so hybrid retrieval has something
to return, while tomorrow's calendar still comes from Google.

Run from asthma-app/ (API need not be running — talks to DB + Google directly):

  COPILOT_DEBUG=1 PYTHONPATH=. python scripts/demo_lobelia_calendar_memory.py \\
    --email lobelia-demo@example.com --password demo-pass-123

  # Seed past soccer/run days so retrieved_episodes is non-empty
  PYTHONPATH=. python scripts/demo_lobelia_calendar_memory.py \\
    --email lobelia-demo@example.com --password demo-pass-123 --seed-episodes

  # Faster: skip live LLM / classifier (still shows calendar + episodes)
  PYTHONPATH=. python scripts/demo_lobelia_calendar_memory.py \\
    --email lobelia-demo@example.com --password demo-pass-123 --seed-episodes --skip-llm
"""

from __future__ import annotations

import argparse
import asyncio
import json
import os
import sys
from datetime import date, timedelta
from pathlib import Path
from typing import Any

from dotenv import load_dotenv
from sqlalchemy import select

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

load_dotenv(ROOT / ".env", override=False)
os.environ["COPILOT_DEBUG"] = "1"

from copilot.embeddings import StubEmbedder, get_embedder  # noqa: E402
from copilot.llm import LLMRegistry  # noqa: E402
from copilot.providers import StructuredCalendarProvider  # noqa: E402
from copilot.workflow import generate_copilot_advice  # noqa: E402
from db.database import SessionLocal, database_reachable  # noqa: E402
from db.models import CheckIn, EnvSnapshot, User  # noqa: E402
from services.auth_service import verify_password  # noqa: E402
from services.check_in_service import upsert_check_in  # noqa: E402
from services.episode_store import (  # noqa: E402
    soft_upsert_episode_for_forecast,
    upsert_retrospective_from_day,
)
from services.forecast_service import run_forecast  # noqa: E402
from services import google_calendar as gcal  # noqa: E402


class _FakeModel:
    def __init__(self, content: str):
        self._content = content

    async def ainvoke(self, _messages, **_kwargs):
        return type("R", (), {"content": self._content})()


def _print_section(title: str, payload: Any) -> None:
    print("\n" + "=" * 72)
    print(title)
    print("-" * 72)
    if isinstance(payload, (dict, list)):
        print(json.dumps(payload, indent=2, ensure_ascii=False, default=str))
    else:
        print(payload)


def _load_user(db, email: str, password: str) -> User:
    user = db.scalar(select(User).where(User.email == email.lower()))
    if user is None:
        raise SystemExit(
            f"No user for {email}. Register first, then connect Google Calendar."
        )
    if not verify_password(password, user.password_hash):
        raise SystemExit("Invalid password.")
    if not user.google_calendar_refresh_token:
        raise SystemExit(
            "Google Calendar is not connected for this user.\n"
            "Login → GET /v1/calendar/connect → open auth_url → grant access, then retry."
        )
    return user


def _seed_outdoor_episodes(db, user: User, *, anchor: date, embedder) -> list[date]:
    """Create past outdoor-exertion days so hybrid retrieval can match soccer/run."""
    seeded: list[date] = []
    samples = [
        (14, "Outdoor soccer (club pickup)", "Campus intramural fields", True, 2, {"temperature": 14, "tree_pollen": "High", "aqi": 3}),
        (21, "Trail run (outdoor)", "Lakeshore path", True, 1, {"temperature": 10, "tree_pollen": "High", "aqi": 2}),
        (28, "Farmers market + campus walk", "Downtown square", True, 1, {"temperature": 18, "grass_pollen": "High", "aqi": 3}),
        (7, "STAT 120 — Lecture", "Social Sciences 101", False, 0, {"temperature": 22, "tree_pollen": "Low", "aqi": 1}),
        (10, "BIO 201 — Lecture", "Science Hall 214", False, 0, {"temperature": 21, "tree_pollen": "Low", "aqi": 1}),
        (3, "Gym — cardio + weights", "Campus Rec Center", True, 1, {"temperature": 20, "tree_pollen": "Moderate", "aqi": 2}),
    ]
    for days_ago, title, location, day_symp, puffs, env in samples:
        day = anchor - timedelta(days=days_ago)
        check_in = db.scalar(select(CheckIn).where(CheckIn.user_id == user.id, CheckIn.date == day))
        event = {"title": title, "location": location, "start": day.isoformat(), "source": "seed"}
        if check_in is None:
            db.add(
                CheckIn(
                    user_id=user.id,
                    date=day,
                    daily_day_symp=day_symp,
                    daily_night_symp=False,
                    daily_limit_activity=day_symp,
                    symptoms_logged=True,
                    puffs_today=puffs,
                    triggers=["pollen", "exercise"] if day_symp else [],
                    calendar_event=title,
                    calendar_events=[event],
                )
            )
        else:
            check_in.calendar_event = title
            check_in.calendar_events = [event]
            check_in.daily_day_symp = day_symp
            check_in.puffs_today = puffs
            check_in.symptoms_logged = True

        snap = db.scalar(select(EnvSnapshot).where(EnvSnapshot.user_id == user.id, EnvSnapshot.date == day))
        if snap is None:
            db.add(
                EnvSnapshot(
                    user_id=user.id,
                    date=day,
                    lat=42.36,
                    lon=-71.06,
                    provider="seed",
                    features=env,
                    missing=[],
                )
            )
        else:
            snap.features = env
        db.flush()
        upsert_retrospective_from_day(db, user.id, day, environment=env, embedder=embedder)
        seeded.append(day)
    db.commit()
    return seeded


async def main() -> int:
    parser = argparse.ArgumentParser(description="Lobelia Google Calendar + episode memory demo")
    parser.add_argument("--email", default=os.getenv("LOBELIA_DEMO_EMAIL", "lobelia-demo@example.com"))
    parser.add_argument("--password", default=os.getenv("LOBELIA_DEMO_PASSWORD", "demo-pass-123"))
    parser.add_argument("--lat", type=float, default=42.36)
    parser.add_argument("--lon", type=float, default=-71.06)
    parser.add_argument("--timezone", default="America/Chicago")
    parser.add_argument(
        "--seed-episodes",
        action="store_true",
        help="Insert past outdoor check-ins/episodes so retrieved_episodes is non-empty",
    )
    parser.add_argument(
        "--skip-llm",
        action="store_true",
        help="Skip live classifier/LLM; still fetch Google calendar + run episode retrieval",
    )
    parser.add_argument(
        "--embedder",
        choices=["stub", "gemini"],
        default=os.getenv("EMBEDDING_PROVIDER", "stub"),
    )
    args = parser.parse_args()

    if not database_reachable():
        raise SystemExit("Database not reachable. Start Postgres (docker compose up -d).")

    os.environ["EMBEDDING_PROVIDER"] = args.embedder
    embedder = StubEmbedder() if args.embedder == "stub" else get_embedder("gemini")

    db = SessionLocal()
    try:
        user = _load_user(db, args.email, args.password)
        anchor = date.today()
        tomorrow = anchor + timedelta(days=1)

        print(f"User: {user.email}")
        print(f"Google email on file: {user.google_calendar_email or '(not stored)'}")
        print(f"Today (anchor): {anchor.isoformat()}")
        print(f"Tomorrow (calendar window): {tomorrow.isoformat()}")
        print(f"EMBEDDING_PROVIDER={args.embedder}")

        try:
            google_events = await gcal.fetch_events_for_day(
                user.google_calendar_refresh_token,
                day=tomorrow,
                timezone_name=args.timezone,
            )
        except Exception as exc:
            raise SystemExit(
                f"Google Calendar fetch failed for {tomorrow}: {exc}\n"
                "Enable Calendar API / reconnect OAuth, then retry."
            ) from exc

        _print_section(
            f"GOOGLE CALENDAR — {tomorrow.isoformat()} ({len(google_events)} events)",
            [
                {
                    "title": e.get("title"),
                    "start": e.get("start"),
                    "end": e.get("end"),
                    "location": e.get("location"),
                }
                for e in google_events
            ],
        )

        if args.seed_episodes:
            seeded = _seed_outdoor_episodes(db, user, anchor=anchor, embedder=embedder)
            _print_section("SEEDED PAST EPISODE DAYS", [d.isoformat() for d in seeded])

        upsert_check_in(
            db,
            user.id,
            day=anchor,
            daily_day_symp=False,
            daily_night_symp=True,
            daily_limit_activity=False,
            notes="lobelia demo script",
            triggers=["pollen"],
        )
        db.commit()

        if args.skip_llm:
            soft_upsert_episode_for_forecast(db, user.id, anchor, embedder=embedder)
            db.commit()
            fake = json.dumps(
                {
                    "summary": "Demo advice (LLM skipped).",
                    "sections": [
                        {"title": "Demo", "body": "Calendar + episode retrieval still ran."}
                    ],
                    "disclaimer": "Educational only.",
                }
            )
            registry = LLMRegistry(
                factories={
                    "gemini": lambda: _FakeModel(fake),
                    "claude": lambda: _FakeModel(fake),
                },
                retries_per_provider=1,
            )
            advice, warnings, debug = await generate_copilot_advice(
                db=db,
                user=user,
                anchor_date=anchor,
                forecast={
                    "risk_level": "Medium",
                    "flare_probability": 0.55,
                    "contributing_factors": ["High pollen", "Exercise"],
                    "top_features": [],
                },
                environment={"aqi": 3, "tree_pollen": "High", "temperature": 16.0},
                symptoms_summary="nighttime symptoms",
                puffs_today=1,
                calendar_provider=StructuredCalendarProvider(
                    google_events,
                    default_source="google_calendar",
                    pre_scoped=True,
                ),
                calendar_day=tomorrow,
                llm_registry=registry,
            )
            result = {
                "date": anchor.isoformat(),
                "forecast_for": tomorrow.isoformat(),
                "risk_level": "Medium",
                "flare_probability": 0.55,
                "calendar_source": "google_calendar",
                "calendar_events": google_events,
                "advice": advice,
                "warnings": warnings,
                "debug": debug,
                "note": "skip-llm: classifier not run; Google calendar + episode retrieval + fake advice",
            }
        else:
            result = await run_forecast(
                db,
                user,
                lat=args.lat,
                lon=args.lon,
                anchor_date=anchor,
                advice_type="daily",
                timezone_name=args.timezone,
            )

        _print_section(
            "FORECAST SUMMARY",
            {
                "date": result.get("date"),
                "forecast_for": result.get("forecast_for"),
                "risk_level": result.get("risk_level"),
                "flare_probability": result.get("flare_probability"),
                "calendar_source": result.get("calendar_source"),
                "calendar_event_count": len(result.get("calendar_events") or []),
                "note": result.get("note"),
            },
        )
        debug = result.get("debug") or {}
        _print_section("DEBUG.RETRIEVED_EPISODES", debug.get("retrieved_episodes"))
        _print_section("DEBUG.INSIGHTS", debug.get("insights"))
        advice = result.get("advice") or {}
        _print_section("ADVICE SUMMARY", advice.get("summary"))
        return 0
    finally:
        db.close()


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))

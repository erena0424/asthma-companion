#!/usr/bin/env python3
"""Backfill retrospective episodes from existing check-ins + env snapshots.

Usage (from asthma-app/):

  EMBEDDING_PROVIDER=stub PYTHONPATH=. python scripts/backfill_episodes.py
  EMBEDDING_PROVIDER=gemini PYTHONPATH=. python scripts/backfill_episodes.py --email lobelia@example.com
"""

from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path

_ROOT = Path(__file__).resolve().parent.parent
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from dotenv import load_dotenv

load_dotenv(_ROOT / ".env")

from sqlalchemy import select

from copilot.embeddings import get_embedder
from db.database import SessionLocal
from db.models import CheckIn, User
from services.episode_store import upsert_retrospective_from_day


def main() -> int:
    parser = argparse.ArgumentParser(description="Backfill episode memory from check-ins")
    parser.add_argument("--email", help="Only backfill this user email")
    parser.add_argument("--limit", type=int, default=0, help="Max check-in days per user (0 = all)")
    args = parser.parse_args()

    embedder = get_embedder(os.getenv("EMBEDDING_PROVIDER", "stub"))
    db = SessionLocal()
    try:
        users = list(db.scalars(select(User).order_by(User.created_at.asc())).all())
        if args.email:
            users = [u for u in users if u.email.lower() == args.email.lower()]
            if not users:
                print(f"No user found for email={args.email}")
                return 1

        total = 0
        for user in users:
            days = list(
                db.scalars(
                    select(CheckIn.date)
                    .where(CheckIn.user_id == user.id)
                    .order_by(CheckIn.date.asc())
                ).all()
            )
            if args.limit > 0:
                days = days[: args.limit]
            written = 0
            for day in days:
                if upsert_retrospective_from_day(db, user.id, day, embedder=embedder):
                    written += 1
            db.commit()
            total += written
            print(f"{user.email}: upserted {written} episodes")
        print(f"Done. Total episodes touched: {total}")
        return 0
    finally:
        db.close()


if __name__ == "__main__":
    raise SystemExit(main())

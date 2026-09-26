"""Create an idempotent demo user with realistic historical symptom logs."""

from __future__ import annotations

import argparse
import math
import random
import sys
from datetime import date, timedelta
from pathlib import Path

from sqlalchemy import select
from sqlalchemy.engine import make_url

_ROOT = Path(__file__).resolve().parent.parent
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from db.database import DATABASE_URL, SessionLocal, database_reachable
from db.models import CheckIn, User
from services.auth_service import hash_password

DEMO_EMAIL = "history-demo@example.com"
DEMO_PASSWORD = "demo-pass-123"
LOCAL_DB_HOSTS = {None, "localhost", "127.0.0.1", "postgres", "db"}


def _weighted_puffs(rng: random.Random, symptom_count: int) -> int:
    choices = {
        0: ([0, 1, 2], [90, 9, 1]),
        1: ([0, 1, 2, 3], [55, 30, 12, 3]),
        2: ([0, 1, 2, 3, 4], [20, 30, 28, 15, 7]),
        3: ([0, 1, 2, 3, 4, 5], [5, 10, 20, 30, 20, 15]),
    }
    values, weights = choices[symptom_count]
    return rng.choices(values, weights=weights, k=1)[0]


def generate_log(rng: random.Random, day: date, index: int) -> dict:
    """Generate one correlated, non-clinical demo check-in."""
    seasonal_wave = (math.sin((day.timetuple().tm_yday - 80) * 2 * math.pi / 365) + 1) / 2
    flare_episode = index % 47 in range(0, 4)
    symptom_probability = min(0.82, 0.12 + 0.18 * seasonal_wave + (0.42 if flare_episode else 0))

    daytime = rng.random() < symptom_probability
    nighttime = rng.random() < symptom_probability * 0.55
    limited = rng.random() < symptom_probability * 0.38
    symptom_count = sum((daytime, nighttime, limited))
    puffs = _weighted_puffs(rng, symptom_count)

    triggers: list[str] = []
    if symptom_count or puffs:
        if seasonal_wave > 0.55 and rng.random() < 0.58:
            triggers.append("Pollen")
        if rng.random() < 0.28:
            triggers.append("Exercise")
        if rng.random() < 0.16:
            triggers.append("Air pollution")
        if not triggers:
            triggers.append(rng.choice(["Weather change", "Dust", "Unknown"]))

    return {
        "daily_day_symp": daytime,
        "daily_night_symp": nighttime,
        "daily_limit_activity": limited,
        "symptoms_logged": True,
        "puffs_today": puffs,
        "triggers": triggers,
    }


def seed_history(days: int, seed: int) -> tuple[User, date, date, int]:
    if not database_reachable():
        raise RuntimeError(
            "Could not connect to the database. "
            "Start Postgres and run: alembic upgrade head"
        )

    rng = random.Random(seed)
    end_date = date.today() - timedelta(days=1)
    start_date = end_date - timedelta(days=days - 1)

    with SessionLocal() as db:
        user = db.scalar(select(User).where(User.email == DEMO_EMAIL))
        if user is None:
            user = User(
                email=DEMO_EMAIL,
                password_hash=hash_password(DEMO_PASSWORD),
                name="History Demo",
                date_of_birth=date(1994, 6, 15),
                preferred_reminder="morning",
                contact_method="app",
                care_goal="Track symptoms and stay active",
                trigger_preferences=["Pollen", "Exercise", "Air pollution"],
            )
            db.add(user)
            db.flush()
        else:
            user.password_hash = hash_password(DEMO_PASSWORD)

        for index in range(days):
            log_date = start_date + timedelta(days=index)
            values = generate_log(rng, log_date, index)
            check_in = db.scalar(
                select(CheckIn).where(CheckIn.user_id == user.id, CheckIn.date == log_date)
            )
            if check_in is None:
                check_in = CheckIn(user_id=user.id, date=log_date)
                db.add(check_in)
            for field, value in values.items():
                setattr(check_in, field, value)

        db.commit()
        db.refresh(user)
        return user, start_date, end_date, days


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--days", type=int, default=180, help="Number of past days to generate")
    parser.add_argument("--seed", type=int, default=42, help="Random seed for repeatable data")
    parser.add_argument(
        "--allow-remote",
        action="store_true",
        help="Allow writing to a non-local database",
    )
    args = parser.parse_args()
    if args.days < 1 or args.days > 730:
        parser.error("--days must be between 1 and 730")

    database_host = make_url(DATABASE_URL).host
    if database_host not in LOCAL_DB_HOSTS and not args.allow_remote:
        parser.error(
            f"Refusing to seed remote database host {database_host!r}; pass --allow-remote explicitly"
        )

    user, start_date, end_date, count = seed_history(args.days, args.seed)
    print(f"Seeded {count} check-ins for {user.email} ({start_date} through {end_date}).")
    print(f"Demo login: {DEMO_EMAIL} / {DEMO_PASSWORD}")


if __name__ == "__main__":
    main()

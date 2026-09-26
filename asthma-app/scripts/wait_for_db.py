"""Block until PostgreSQL accepts connections."""

from __future__ import annotations

import os
import sys
import time

from sqlalchemy import create_engine, text


def main() -> None:
    url = os.environ.get("DATABASE_URL")
    if not url:
        print("DATABASE_URL is not set", file=sys.stderr)
        sys.exit(1)

    engine = create_engine(url, pool_pre_ping=True)
    for attempt in range(1, 61):
        try:
            with engine.connect() as conn:
                conn.execute(text("SELECT 1"))
            print("Database is ready.")
            return
        except Exception as exc:
            print(f"Waiting for database ({attempt}/60): {exc}")
            time.sleep(1)

    print("Database did not become ready in time.", file=sys.stderr)
    sys.exit(1)


if __name__ == "__main__":
    main()

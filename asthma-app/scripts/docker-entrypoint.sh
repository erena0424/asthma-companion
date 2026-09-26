#!/usr/bin/env sh
set -eu

cd /app

python scripts/wait_for_db.py
alembic upgrade head

exec "$@"

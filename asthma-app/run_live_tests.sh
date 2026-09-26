#!/usr/bin/env bash
# Run live API integration tests (OpenWeather, Google Pollen, Gemini/Claude).
# Requires keys in .env and Docker Postgres for DB-backed tests.
set -euo pipefail
ROOT="$(cd "$(dirname "$0")" && pwd)"
cd "$ROOT"
export PYTHONPATH="$ROOT${PYTHONPATH:+:$PYTHONPATH}"
export RUN_LIVE_API_TESTS=1
PYTEST="pytest"
if [[ -x "$ROOT/.venv/bin/pytest" ]]; then
  PYTEST="$ROOT/.venv/bin/pytest"
fi
exec "$PYTEST" -m live -v "$@"

#!/usr/bin/env bash
# Run pytest with asthma-app on PYTHONPATH (same layout as ./run_api.sh).
set -euo pipefail
ROOT="$(cd "$(dirname "$0")" && pwd)"
cd "$ROOT"
export PYTHONPATH="$ROOT${PYTHONPATH:+:$PYTHONPATH}"
PYTEST="pytest"
if [[ -x "$ROOT/.venv/bin/pytest" ]]; then
  PYTEST="$ROOT/.venv/bin/pytest"
fi
exec "$PYTEST" "$@"

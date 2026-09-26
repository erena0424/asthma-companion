#!/usr/bin/env bash
# Quick LLM advice check — see scripts/check_llm_advice.py for options.
set -euo pipefail
ROOT="$(cd "$(dirname "$0")" && pwd)"
cd "$ROOT"
export PYTHONPATH="$ROOT${PYTHONPATH:+:$PYTHONPATH}"
PYTHON="python3"
if [[ -x "$ROOT/.venv/bin/python" ]]; then
  PYTHON="$ROOT/.venv/bin/python"
fi
exec "$PYTHON" scripts/check_llm_advice.py "$@"

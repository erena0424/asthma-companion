#!/usr/bin/env bash
# Run from anywhere; uvicorn needs asthma-app as --app-dir so `api` and `model` import.
set -euo pipefail
ROOT="$(cd "$(dirname "$0")" && pwd)"
cd "$ROOT"
exec uvicorn api.main:app --reload --app-dir "$ROOT" --host 127.0.0.1 --port 8000

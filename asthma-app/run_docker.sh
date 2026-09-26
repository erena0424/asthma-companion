#!/usr/bin/env bash
# Start Mirror Lake with free Docker Engine (Colima / Docker Desktop Personal).
set -euo pipefail

ROOT="$(cd "$(dirname "$0")" && pwd)"
cd "$ROOT"

if ! command -v docker >/dev/null 2>&1; then
  echo "Docker CLI not found."
  echo "Install free local Docker: ./scripts/install_docker_mac.sh"
  exit 1
fi

compose() {
  if docker compose version >/dev/null 2>&1; then
    docker compose "$@"
  elif command -v docker-compose >/dev/null 2>&1; then
    docker-compose "$@"
  else
    echo "Docker Compose not found. Run ./scripts/install_docker_mac.sh"
    exit 1
  fi
}

if ! docker info >/dev/null 2>&1; then
  echo "Docker daemon is not running."
  if command -v colima >/dev/null 2>&1; then
    echo "Starting Colima..."
    colima start --cpu 2 --memory 4 --disk 20
  else
    echo "Start Docker Desktop or run: colima start"
    exit 1
  fi
fi

if [[ ! -f .env ]]; then
  echo "Creating .env from .env.example (edit API keys as needed)..."
  cp .env.example .env
  # JWT placeholder fails at import — set a dev default for Docker.
  if grep -q '^JWT_SECRET=change_me_in_production' .env; then
    sed -i '' 's/^JWT_SECRET=change_me_in_production/JWT_SECRET=dev_local_docker_jwt_secret_not_for_production/' .env 2>/dev/null \
      || sed -i 's/^JWT_SECRET=change_me_in_production/JWT_SECRET=dev_local_docker_jwt_secret_not_for_production/' .env
  fi
fi

CMD="${1:-up}"
shift || true

case "$CMD" in
  up)
    compose up --build -d "$@"
    echo ""
    echo "API:     http://127.0.0.1:8000/docs"
    echo "Health:  http://127.0.0.1:8000/health"
    echo "Logs:    compose logs -f api  (or: ./run_docker.sh logs)"
    ;;
  dev)
    compose --profile dev up --build api-dev postgres "$@"
    ;;
  down)
    compose --profile dev --profile test down "$@"
    ;;
  test)
    compose --profile test run --rm test "$@"
    ;;
  logs)
    compose logs -f api "$@"
    ;;
  smoke)
    compose up -d --build
    sleep 5
    python3 scripts/smoke_integration.py
    ;;
  *)
    compose "$CMD" "$@"
    ;;
esac

#!/usr/bin/env bash
# Install free Docker tooling on macOS (no paid Docker Desktop subscription required).
# Uses Colima (free, open source) + Docker CLI + Compose plugin via Homebrew.
set -euo pipefail

if [[ "$(uname -s)" != "Darwin" ]]; then
  echo "This installer targets macOS. On Linux, install Docker Engine from your distro."
  echo "On Windows, install Docker Desktop (free Personal tier) or WSL2 + Docker Engine."
  exit 1
fi

if ! command -v brew >/dev/null 2>&1; then
  echo "Homebrew is required: https://brew.sh"
  exit 1
fi

echo "Installing Colima + Docker CLI (free)..."
brew install colima docker docker-compose

# Docker Compose v2 plugin path (Homebrew)
mkdir -p "$HOME/.docker"
python3 <<'PY'
import json, os
p = os.path.expanduser("~/.docker/config.json")
cfg = {}
if os.path.exists(p):
    with open(p) as f:
        cfg = json.load(f)
extra = "/opt/homebrew/lib/docker/cli-plugins"
dirs = cfg.setdefault("cliPluginsExtraDirs", [])
if extra not in dirs:
    dirs.append(extra)
with open(p, "w") as f:
    json.dump(cfg, f, indent=2)
PY

echo "Starting Colima VM (2 CPU, 4GB RAM)..."
colima start --cpu 2 --memory 4 --disk 20

echo ""
echo "Docker is ready."
docker --version
if docker compose version >/dev/null 2>&1; then
  docker compose version
else
  docker-compose version
fi
echo ""
echo "Next: cd asthma-app && ./run_docker.sh up"

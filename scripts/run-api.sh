#!/usr/bin/env bash
# run-api.sh
# Responsibility: Start apps/api for local development.

set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
API_DIR="$ROOT_DIR/apps/api"
cd "$API_DIR"

if [[ -f "$API_DIR/.venv/bin/activate" ]]; then
  # shellcheck disable=SC1091
  source "$API_DIR/.venv/bin/activate"
elif [[ -f "$ROOT_DIR/.venv/bin/activate" ]]; then
  # shellcheck disable=SC1091
  source "$ROOT_DIR/.venv/bin/activate"
fi

if ! command -v uvicorn >/dev/null 2>&1; then
  echo "uvicorn not found. Install the API package first:"
  echo "  cd apps/api && python -m venv .venv && source .venv/bin/activate && pip install -e \".[dev]\""
  exit 1
fi

export PYTHONPATH="$API_DIR${PYTHONPATH:+:$PYTHONPATH}"

echo "SitePilot AI — starting API on http://127.0.0.1:8000"
exec uvicorn app.main:app --reload --host 127.0.0.1 --port 8000

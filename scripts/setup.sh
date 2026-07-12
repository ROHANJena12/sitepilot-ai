#!/usr/bin/env bash
# setup.sh
# Responsibility: Bootstrap the local SitePilot AI development environment.
# Scaffold only — install and configure steps will be filled in when apps exist.

set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT_DIR"

echo "SitePilot AI — setup (scaffold)"
echo "TODO: copy .env.example → .env if missing"
echo "TODO: pnpm install"
echo "TODO: prepare local data services (docker compose)"
echo "Setup placeholder complete."

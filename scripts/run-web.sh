#!/usr/bin/env bash
# run-web.sh
# Responsibility: Start apps/web (Next.js) for local development.

set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT_DIR"

if [[ ! -d "apps/web/node_modules" && ! -d "node_modules" ]]; then
  echo "Dependencies missing. Run: pnpm install"
  exit 1
fi

pnpm --filter @sitepilot/web dev

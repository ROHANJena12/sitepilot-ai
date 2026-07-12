#!/usr/bin/env bash
# lint.sh
# Responsibility: Run lint checks across the SitePilot AI monorepo.
# Scaffold only — no linters are invoked yet.

set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT_DIR"

echo "SitePilot AI — lint (scaffold)"
echo "TODO: pnpm lint / turbo run lint"
echo "Lint placeholder complete."

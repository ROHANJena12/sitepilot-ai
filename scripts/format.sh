#!/usr/bin/env bash
# format.sh
# Responsibility: Run formatters across the SitePilot AI monorepo.
# Scaffold only — no formatters are invoked yet.

set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT_DIR"

echo "SitePilot AI — format (scaffold)"
echo "TODO: pnpm format / turbo run format"
echo "Format placeholder complete."

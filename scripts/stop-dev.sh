#!/usr/bin/env bash
# stop-dev.sh — Stop SitePilot local backend + frontend.

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=lib/dev-common.sh
source "${SCRIPT_DIR}/lib/dev-common.sh"

require_repo_root
ensure_runtime_dirs

api_pid="$(read_live_pid "${API_PID_FILE}" || true)"
web_pid="$(read_live_pid "${WEB_PID_FILE}" || true)"

info "Stopping backend..."
if [[ -n "${api_pid}" ]]; then
  stop_pid_tree "${api_pid}" "backend"
else
  info "  (already stopped)"
fi
rm -f "${API_PID_FILE}"

info "Stopping frontend..."
if [[ -n "${web_pid}" ]]; then
  stop_pid_tree "${web_pid}" "frontend"
else
  info "  (already stopped)"
fi
rm -f "${WEB_PID_FILE}"

info "Done."

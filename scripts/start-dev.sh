#!/usr/bin/env bash
# start-dev.sh — Start SitePilot local backend + frontend.

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=lib/dev-common.sh
source "${SCRIPT_DIR}/lib/dev-common.sh"

require_repo_root
ensure_runtime_dirs

info "${C_BOLD}Starting SitePilot development environment...${C_RESET}"
info ""

# 1–3: dirs already ensured
# 4: Docker + DATABASE_URL PostgreSQL (fatal if unavailable)
ensure_database_ready
info ""

# 5: Backend venv
if [[ ! -f "${API_DIR}/.venv/bin/activate" ]]; then
  err "Backend virtual environment missing: apps/api/.venv"
  info ""
  info "Create it with:"
  info "  cd apps/api"
  info "  python3 -m venv .venv"
  info "  source .venv/bin/activate"
  info "  pip install -e \".[dev]\""
  exit 1
fi
ok "Backend venv found"

# 6: Frontend deps (do not auto-install)
if [[ ! -d "${WEB_DIR}/node_modules" ]] && [[ ! -d "${ROOT_DIR}/node_modules" ]]; then
  err "Frontend dependencies missing (node_modules)."
  info ""
  info "Run:"
  info "  npm install"
  info ""
  info "(This monorepo also supports: pnpm install)"
  exit 1
fi
ok "Frontend dependencies found"

# 7: .env warn only
if [[ ! -f "${API_DIR}/.env" ]]; then
  warn "apps/api/.env is missing — API may fail to start. Copy from apps/api/.env.example"
else
  ok "apps/api/.env found"
fi
if [[ ! -f "${WEB_DIR}/.env.local" ]] && [[ ! -f "${WEB_DIR}/.env" ]]; then
  warn "apps/web/.env.local (or .env) is missing — copy from apps/web/.env.example if needed"
fi
info ""

# Already managed by us?
existing_api="$(read_live_pid "${API_PID_FILE}" || true)"
existing_web="$(read_live_pid "${WEB_PID_FILE}" || true)"
if [[ -n "${existing_api}" ]] || [[ -n "${existing_web}" ]]; then
  err "Dev processes already appear to be running (see ./scripts/status.sh)."
  err "Stop them first: ./scripts/stop-dev.sh"
  exit 1
fi

# 8: Ports
assert_port_free "${API_PORT}" "Backend"
assert_port_free "${WEB_PORT}" "Frontend"
ok "Ports ${API_PORT} and ${WEB_PORT} are free"
info ""

# 9: Start backend
info "Starting backend (uvicorn)..."
(
  cd "${API_DIR}"
  # shellcheck disable=SC1091
  source "${API_DIR}/.venv/bin/activate"
  export PYTHONPATH="${API_DIR}${PYTHONPATH:+:${PYTHONPATH}}"
  if command -v setsid >/dev/null 2>&1; then
    nohup setsid uvicorn app.main:app --reload --host 127.0.0.1 --port "${API_PORT}" \
      >>"${API_LOG_FILE}" 2>&1 &
  else
    nohup uvicorn app.main:app --reload --host 127.0.0.1 --port "${API_PORT}" \
      >>"${API_LOG_FILE}" 2>&1 &
  fi
  echo $! >"${API_PID_FILE}"
)
api_pid="$(tr -d '[:space:]' < "${API_PID_FILE}")"
ok "Backend started (pid ${api_pid})"

# 10: Wait for health
if ! wait_for_http "${API_HEALTH_URL}" "backend" 60; then
  err "Backend failed to become healthy. Tail of ${API_LOG_FILE}:"
  tail -n 40 "${API_LOG_FILE}" >&2 || true
  exit 1
fi
ok "Backend healthy at ${API_HEALTH_URL}"
info ""

# 11: Start frontend on WEB_PORT (CLI override; does not change package.json)
info "Starting frontend (Next.js on port ${WEB_PORT})..."
(
  cd "${WEB_DIR}"
  if command -v pnpm >/dev/null 2>&1 && [[ -f "${ROOT_DIR}/pnpm-lock.yaml" ]]; then
    if command -v setsid >/dev/null 2>&1; then
      nohup setsid pnpm exec next dev --port "${WEB_PORT}" >>"${WEB_LOG_FILE}" 2>&1 &
    else
      nohup pnpm exec next dev --port "${WEB_PORT}" >>"${WEB_LOG_FILE}" 2>&1 &
    fi
  else
    if command -v setsid >/dev/null 2>&1; then
      nohup setsid npm run dev -- --port "${WEB_PORT}" >>"${WEB_LOG_FILE}" 2>&1 &
    else
      nohup npm run dev -- --port "${WEB_PORT}" >>"${WEB_LOG_FILE}" 2>&1 &
    fi
  fi
  echo $! >"${WEB_PID_FILE}"
)
web_pid="$(tr -d '[:space:]' < "${WEB_PID_FILE}")"
ok "Frontend started (pid ${web_pid})"

# 12: Wait for web
if ! wait_for_http "${WEB_URL}" "frontend" 90; then
  err "Frontend failed to become ready. Tail of ${WEB_LOG_FILE}:"
  tail -n 40 "${WEB_LOG_FILE}" >&2 || true
  exit 1
fi
ok "Frontend ready at ${WEB_URL}"
info ""

# 13: Browser
open_browser "${WEB_URL}"

# 14: Summary
cat <<EOF

======================================
SitePilot Development Environment
======================================

✓ Backend running
  http://localhost:${API_PORT}

✓ Frontend running
  http://localhost:${WEB_PORT}

✓ API log
  logs/api.log

✓ Frontend log
  logs/web.log

======================================

EOF

#!/usr/bin/env bash
# status.sh — Show SitePilot local development process status.

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=lib/dev-common.sh
source "${SCRIPT_DIR}/lib/dev-common.sh"

require_repo_root
ensure_runtime_dirs

api_pid="$(read_live_pid "${API_PID_FILE}" || true)"
web_pid="$(read_live_pid "${WEB_PID_FILE}" || true)"

# Prefer DATABASE_URL from apps/api/.env for accurate host:port status.
db_host="-"
db_port="-"
db_name="-"
pg_status="Unknown"
if [[ -f "${API_ENV_FILE}" ]]; then
  if url="$(read_env_value "${API_ENV_FILE}" "DATABASE_URL" 2>/dev/null)"; then
    if parse_database_url "${url}"; then
      db_host="${DB_HOST}"
      db_port="${DB_PORT}"
      db_name="${DB_NAME:-"-"}"
      pg_status="$(postgres_status)"
    fi
  fi
fi


print_service() {
  local name="$1"
  local pid="$2"
  local port="$3"
  local url="$4"

  printf '\n%s%s%s\n' "${C_BOLD}" "${name}" "${C_RESET}"
  if [[ -n "${pid}" ]]; then
    printf '  Status: %sRunning%s\n' "${C_GREEN}" "${C_RESET}"
    printf '  PID:    %s\n' "${pid}"
  else
    printf '  Status: %sStopped%s\n' "${C_DIM}" "${C_RESET}"
    printf '  PID:    -\n'
  fi
  printf '  Port:   %s\n' "${port}"
  if port_in_use "${port}"; then
    printf '  Listen: yes'
    if http_up "${url}"; then
      printf ' (HTTP ok)\n'
    else
      printf ' (HTTP not ready)\n'
    fi
  else
    printf '  Listen: no\n'
  fi
}

cat <<EOF
${C_BOLD}SitePilot development status${C_RESET}
Root: ${ROOT_DIR}
EOF

print_service "Backend" "${api_pid}" "${API_PORT}" "${API_HEALTH_URL}"
print_service "Frontend" "${web_pid}" "${WEB_PORT}" "${WEB_URL}"

printf '\n%sPostgreSQL%s\n' "${C_BOLD}" "${C_RESET}"
printf '  DATABASE_URL host:port: %s:%s\n' "${db_host}" "${db_port}"
printf '  Database: %s\n' "${db_name}"
case "${pg_status}" in
  Running)
    printf '  Status: %sReachable%s\n' "${C_GREEN}" "${C_RESET}"
    if docker_daemon_running; then
      printf '  Docker: running\n'
    else
      printf '  Docker: not running\n'
    fi
    ;;
  Stopped)
    printf '  Status: %sNot reachable%s\n' "${C_YELLOW}" "${C_RESET}"
    if docker_daemon_running; then
      printf '  Docker: running\n'
    else
      printf '  Docker: not running\n'
    fi
    ;;
  *)
    printf '  Status: %sUnknown%s\n' "${C_DIM}" "${C_RESET}"
    ;;
esac

cat <<EOF

Logs
  API:      logs/api.log
  Frontend: logs/web.log

PID files
  API:      .pids/api.pid
  Frontend: .pids/web.pid

EOF

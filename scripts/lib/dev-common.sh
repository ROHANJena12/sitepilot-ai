#!/usr/bin/env bash
# Shared helpers for SitePilot local development scripts.
# shellcheck disable=SC2034

set -euo pipefail

# Resolve repo root from any script that sources this file.
_SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="$(cd "${_SCRIPT_DIR}/../.." && pwd)"

API_DIR="${ROOT_DIR}/apps/api"
WEB_DIR="${ROOT_DIR}/apps/web"
LOG_DIR="${ROOT_DIR}/logs"
PID_DIR="${ROOT_DIR}/.pids"

API_PID_FILE="${PID_DIR}/api.pid"
WEB_PID_FILE="${PID_DIR}/web.pid"
API_LOG_FILE="${LOG_DIR}/api.log"
WEB_LOG_FILE="${LOG_DIR}/web.log"

API_PORT=8000
WEB_PORT=5173
API_HEALTH_URL="http://localhost:${API_PORT}/health"
WEB_URL="http://localhost:${WEB_PORT}"

# ----- Colors (when stdout is a TTY) -----
if [[ -t 1 ]] && command -v tput >/dev/null 2>&1 && [[ "$(tput colors 2>/dev/null || echo 0)" -ge 8 ]]; then
  C_RESET="$(tput sgr0)"
  C_GREEN="$(tput setaf 2)"
  C_YELLOW="$(tput setaf 3)"
  C_RED="$(tput setaf 1)"
  C_BOLD="$(tput bold)"
  C_DIM="$(tput dim)"
else
  C_RESET="" C_GREEN="" C_YELLOW="" C_RED="" C_BOLD="" C_DIM=""
fi

ok()   { printf '%s✓%s %s\n' "${C_GREEN}" "${C_RESET}" "$*"; }
warn() { printf '%s⚠%s %s\n' "${C_YELLOW}" "${C_RESET}" "$*"; }
err()  { printf '%s✗%s %s\n' "${C_RED}" "${C_RESET}" "$*" >&2; }
info() { printf '%s\n' "$*"; }

require_repo_root() {
  if [[ ! -f "${ROOT_DIR}/pnpm-workspace.yaml" ]] || [[ ! -d "${ROOT_DIR}/apps/api" ]] || [[ ! -d "${ROOT_DIR}/apps/web" ]]; then
    err "Not the SitePilot repository root (expected apps/api, apps/web, pnpm-workspace.yaml)."
    err "Run from the repo: ./scripts/start-dev.sh"
    exit 1
  fi
}

ensure_runtime_dirs() {
  mkdir -p "${LOG_DIR}" "${PID_DIR}"
}

# Return 0 if TCP port is in use.
port_in_use() {
  local port="$1"
  if command -v lsof >/dev/null 2>&1; then
    lsof -nP -iTCP:"${port}" -sTCP:LISTEN >/dev/null 2>&1
  elif command -v nc >/dev/null 2>&1; then
    nc -z 127.0.0.1 "${port}" >/dev/null 2>&1
  else
    return 1
  fi
}

describe_port_owner() {
  local port="$1"
  if command -v lsof >/dev/null 2>&1; then
    lsof -nP -iTCP:"${port}" -sTCP:LISTEN 2>/dev/null | awk 'NR==1 || NR==2 {print}' || true
  else
    echo "(install lsof to see which process owns the port)"
  fi
}

assert_port_free() {
  local port="$1"
  local label="$2"
  if port_in_use "${port}"; then
    err "${label} port ${port} is already in use:"
    describe_port_owner "${port}" >&2
    exit 1
  fi
}

# Read a PID file; echo PID if process is alive, else empty. Clears stale files.
read_live_pid() {
  local pid_file="$1"
  if [[ ! -f "${pid_file}" ]]; then
    return 0
  fi
  local pid
  pid="$(tr -d '[:space:]' < "${pid_file}" || true)"
  if [[ -z "${pid}" ]] || ! [[ "${pid}" =~ ^[0-9]+$ ]]; then
    rm -f "${pid_file}"
    return 0
  fi
  if kill -0 "${pid}" 2>/dev/null; then
    printf '%s' "${pid}"
  else
    rm -f "${pid_file}"
  fi
}

# Recursively collect descendant PIDs (uvicorn --reload / Next spawn children).
_collect_descendants() {
  local parent="$1"
  local child
  if ! command -v pgrep >/dev/null 2>&1; then
    return 0
  fi
  while IFS= read -r child; do
    [[ -z "${child}" ]] && continue
    _collect_descendants "${child}"
    printf '%s\n' "${child}"
  done < <(pgrep -P "${parent}" 2>/dev/null || true)
}

# Kill a process tree gently, then force if needed. Ignores missing processes.
stop_pid_tree() {
  local pid="$1"
  local label="$2"
  if [[ -z "${pid}" ]]; then
    return 0
  fi
  if ! kill -0 "${pid}" 2>/dev/null; then
    return 0
  fi
  info "Stopping ${label} (pid ${pid})..."

  local targets=()
  local desc
  while IFS= read -r desc; do
    [[ -n "${desc}" ]] && targets+=("${desc}")
  done < <(_collect_descendants "${pid}")
  targets+=("${pid}")

  local t
  for t in "${targets[@]}"; do
    kill -TERM "${t}" 2>/dev/null || true
  done
  # Also try process-group signal when the launcher used setsid (Linux).
  kill -TERM "-${pid}" 2>/dev/null || true

  local i
  for i in 1 2 3 4 5 6 7 8 9 10; do
    local any_alive=0
    for t in "${targets[@]}"; do
      if kill -0 "${t}" 2>/dev/null; then
        any_alive=1
        break
      fi
    done
    if (( any_alive == 0 )); then
      return 0
    fi
    sleep 0.3
  done
  for t in "${targets[@]}"; do
    kill -KILL "${t}" 2>/dev/null || true
  done
  kill -KILL "-${pid}" 2>/dev/null || true
}

wait_for_http() {
  local url="$1"
  local label="$2"
  local timeout_s="${3:-60}"
  local elapsed=0
  info "Waiting for ${label} (${url})..."
  while (( elapsed < timeout_s )); do
    if command -v curl >/dev/null 2>&1; then
      if curl -sf --max-time 2 "${url}" >/dev/null 2>&1; then
        return 0
      fi
    elif command -v wget >/dev/null 2>&1; then
      if wget -q --timeout=2 -O /dev/null "${url}" 2>/dev/null; then
        return 0
      fi
    else
      err "Neither curl nor wget is available to poll ${url}."
      exit 1
    fi
    sleep 1
    elapsed=$((elapsed + 1))
  done
  err "${label} did not become ready within ${timeout_s}s. See logs."
  return 1
}

http_up() {
  local url="$1"
  if command -v curl >/dev/null 2>&1; then
    curl -sf --max-time 2 "${url}" >/dev/null 2>&1
  elif command -v wget >/dev/null 2>&1; then
    wget -q --timeout=2 -O /dev/null "${url}" 2>/dev/null
  else
    return 1
  fi
}

open_browser() {
  local url="$1"
  case "$(uname -s)" in
    Darwin)
      open "${url}" >/dev/null 2>&1 || true
      ;;
    Linux)
      if command -v xdg-open >/dev/null 2>&1; then
        xdg-open "${url}" >/dev/null 2>&1 || true
      fi
      ;;
    MINGW*|MSYS*|CYGWIN*)
      start "${url}" >/dev/null 2>&1 || true
      ;;
    *)
      warn "Open ${url} in your browser (no auto-open for this OS)."
      ;;
  esac
}

# ----- Docker + DATABASE_URL–aware PostgreSQL -----

COMPOSE_FILE="${ROOT_DIR}/docker-compose.yml"
COMPOSE_DB_SERVICE="db"
API_ENV_FILE="${API_DIR}/.env"
DOCKER_WAIT_TIMEOUT_S=90
POSTGRES_WAIT_TIMEOUT_S=60

# Populated by load_database_url_from_env / parse_database_url.
DB_URL=""
DB_HOST=""
DB_PORT=""
DB_USER=""
DB_NAME=""

docker_cli_available() {
  command -v docker >/dev/null 2>&1
}

docker_daemon_running() {
  docker_cli_available || return 1
  docker info >/dev/null 2>&1
}

detect_os_family() {
  case "$(uname -s)" in
    Darwin) echo "macos" ;;
    Linux) echo "linux" ;;
    MINGW*|MSYS*|CYGWIN*) echo "windows" ;;
    *) echo "unknown" ;;
  esac
}

# Spinner on stderr while a check command fails; returns 0 when check succeeds.
wait_until() {
  local timeout_s="$1"
  local label="$2"
  shift 2
  local elapsed=0
  local spin='|/-\'
  local i=0
  local tty_err=0
  [[ -t 2 ]] && tty_err=1

  while (( elapsed < timeout_s )); do
    if "$@"; then
      if (( tty_err )); then
        printf '\r\033[K' >&2
      fi
      return 0
    fi
    if (( tty_err )); then
      printf '\r%s %s... %s' "${label}" "$((timeout_s - elapsed))s left" "${spin:i++%${#spin}:1}" >&2
    elif (( elapsed % 5 == 0 )); then
      info "${label} (${elapsed}s / ${timeout_s}s)..."
    fi
    sleep 1
    elapsed=$((elapsed + 1))
  done
  if (( tty_err )); then
    printf '\r\033[K' >&2
  fi
  return 1
}

# Launch Docker Desktop on macOS when the daemon is down.
try_launch_docker_desktop() {
  local os
  os="$(detect_os_family)"
  case "${os}" in
    macos)
      if [[ -d "/Applications/Docker.app" ]] || [[ -d "${HOME}/Applications/Docker.app" ]]; then
        info "Starting Docker Desktop..."
        open -a Docker >/dev/null 2>&1 || true
        return 0
      fi
      err "Docker Desktop app not found. Install Docker Desktop, then retry."
      return 1
      ;;
    windows)
      if command -v powershell.exe >/dev/null 2>&1; then
        info "Starting Docker Desktop..."
        powershell.exe -NoProfile -Command "Start-Process 'Docker Desktop'" >/dev/null 2>&1 || true
        return 0
      fi
      err "Docker daemon is not running. Start Docker Desktop, then retry."
      return 1
      ;;
    linux)
      err "Docker daemon is not running."
      info "Start it, then retry — for example:"
      info "  sudo systemctl start docker"
      info "  # or start Docker Desktop / your distro's Docker service"
      return 1
      ;;
    *)
      err "Docker daemon is not running. Start Docker, then retry."
      return 1
      ;;
  esac
}

ensure_docker_ready() {
  if ! docker_cli_available; then
    err "Docker CLI not found on PATH."
    info "Install Docker Desktop (or Docker Engine) and ensure \`docker\` works."
    exit 1
  fi

  if docker_daemon_running; then
    ok "Docker running"
    return 0
  fi

  if ! try_launch_docker_desktop; then
    exit 1
  fi

  # Linux path already printed instructions and returned failure.
  if [[ "$(detect_os_family)" == "linux" ]]; then
    exit 1
  fi

  info "Waiting for Docker daemon..."
  if wait_until "${DOCKER_WAIT_TIMEOUT_S}" "Waiting for Docker daemon" docker_daemon_running; then
    ok "Docker is ready"
    return 0
  fi

  err "Docker did not become ready within ${DOCKER_WAIT_TIMEOUT_S} seconds."
  info "Please start Docker Desktop manually."
  exit 1
}

# Parse a SQLAlchemy/asyncpg-style URL into DB_* globals.
parse_database_url() {
  local url="$1"
  DB_URL="${url}"
  DB_HOST=""
  DB_PORT=""
  DB_USER=""
  DB_NAME=""

  # Drop query/fragment.
  url="${url%%\?*}"
  url="${url%%\#*}"

  local rest="${url#*://}"
  if [[ "${rest}" == "${url}" ]]; then
    return 1
  fi

  local hostport path
  if [[ "${rest}" == *"@"* ]]; then
    local userinfo="${rest%%@*}"
    rest="${rest#*@}"
    DB_USER="${userinfo%%:*}"
  fi

  hostport="${rest%%/*}"
  if [[ "${rest}" == */* ]]; then
    path="${rest#*/}"
    DB_NAME="${path%%/*}"
  fi

  if [[ "${hostport}" == \[*\]* ]]; then
    # Rare IPv6 form: [::1]:5434
    DB_HOST="${hostport%%]*}"
    DB_HOST="${DB_HOST#\[}"
    local after=":${hostport#*\]}"
    if [[ "${after}" == :* && "${after}" != : ]]; then
      DB_PORT="${after#:}"
    else
      DB_PORT="5432"
    fi
  elif [[ "${hostport}" == *:* ]]; then
    DB_HOST="${hostport%%:*}"
    DB_PORT="${hostport##*:}"
  else
    DB_HOST="${hostport}"
    DB_PORT="5432"
  fi

  [[ -n "${DB_HOST}" && -n "${DB_PORT}" ]] || return 1
  [[ "${DB_PORT}" =~ ^[0-9]+$ ]] || return 1
  return 0
}

read_env_value() {
  local file="$1"
  local key="$2"
  local line value
  while IFS= read -r line || [[ -n "${line}" ]]; do
    line="${line#"${line%%[![:space:]]*}"}"
    [[ -z "${line}" || "${line}" == \#* ]] && continue
    if [[ "${line}" == "${key}="* ]]; then
      value="${line#*=}"
      value="${value%$'\r'}"
      # Strip matching single/double quotes.
      if [[ "${value}" == \"*\" && "${value}" == *\" ]]; then
        value="${value:1:${#value}-2}"
      elif [[ "${value}" == \'*\' && "${value}" == *\' ]]; then
        value="${value:1:${#value}-2}"
      fi
      printf '%s' "${value}"
      return 0
    fi
  done < "${file}"
  return 1
}

load_database_url_from_env() {
  if [[ ! -f "${API_ENV_FILE}" ]]; then
    err "Missing ${API_ENV_FILE} — cannot validate DATABASE_URL."
    info "Copy apps/api/.env.example to apps/api/.env and set DATABASE_URL."
    exit 1
  fi
  local url
  if ! url="$(read_env_value "${API_ENV_FILE}" "DATABASE_URL")"; then
    err "DATABASE_URL not found in apps/api/.env"
    exit 1
  fi
  if [[ -z "${url}" ]]; then
    err "DATABASE_URL is empty in apps/api/.env"
    exit 1
  fi
  if ! parse_database_url "${url}"; then
    err "Could not parse DATABASE_URL from apps/api/.env"
    info "Expected form: postgresql+asyncpg://user:pass@host:port/dbname"
    info "Got: ${url}"
    exit 1
  fi
}

db_host_is_local() {
  case "${DB_HOST}" in
    localhost|127.0.0.1|0.0.0.0|::1) return 0 ;;
    *) return 1 ;;
  esac
}

# TCP reachability for the exact DATABASE_URL host:port.
database_port_reachable() {
  local host="${1:-${DB_HOST}}"
  local port="${2:-${DB_PORT}}"
  if command -v nc >/dev/null 2>&1; then
    nc -z -w 2 "${host}" "${port}" >/dev/null 2>&1
    return $?
  fi
  if command -v timeout >/dev/null 2>&1; then
    timeout 2 bash -c "echo >/dev/tcp/${host}/${port}" >/dev/null 2>&1
    return $?
  fi
  # macOS bash may support /dev/tcp without timeout.
  (echo >/dev/tcp/"${host}"/"${port}") >/dev/null 2>&1
}

database_pg_isready() {
  local host="${1:-${DB_HOST}}"
  local port="${2:-${DB_PORT}}"
  local user="${3:-${DB_USER}}"
  if ! command -v pg_isready >/dev/null 2>&1; then
    # Fall back to TCP when client tools are not installed.
    database_port_reachable "${host}" "${port}"
    return $?
  fi
  if [[ -n "${user}" ]]; then
    pg_isready -h "${host}" -p "${port}" -U "${user}" -q 2>/dev/null
  else
    pg_isready -h "${host}" -p "${port}" -q 2>/dev/null
  fi
}

database_reachable() {
  database_pg_isready "${DB_HOST}" "${DB_PORT}" "${DB_USER}"
}

print_database_diagnostics() {
  local docker_yes_no="no"
  local port_yes_no="no"
  local pg_yes_no="no"
  docker_daemon_running && docker_yes_no="yes"
  database_port_reachable && port_yes_no="yes"
  if command -v pg_isready >/dev/null 2>&1; then
    if [[ -n "${DB_USER}" ]]; then
      pg_isready -h "${DB_HOST}" -p "${DB_PORT}" -U "${DB_USER}" -q 2>/dev/null && pg_yes_no="yes"
    else
      pg_isready -h "${DB_HOST}" -p "${DB_PORT}" -q 2>/dev/null && pg_yes_no="yes"
    fi
  else
    pg_yes_no="n/a (pg_isready not installed)"
    [[ "${port_yes_no}" == "yes" ]] && pg_yes_no="n/a (pg_isready not installed; port open)"
  fi

  cat <<EOF >&2

Expected database:
  Host:     ${DB_HOST}
  Port:     ${DB_PORT}
  Database: ${DB_NAME:-'(unknown)'}
  User:     ${DB_USER:-'(unknown)'}
  Source:   apps/api/.env (DATABASE_URL)

Actual check:
  Docker running: ${docker_yes_no}
  Port reachable: ${port_yes_no}
  pg_isready:     ${pg_yes_no}

EOF
}

compose_cmd() {
  if docker compose version >/dev/null 2>&1; then
    docker compose -f "${COMPOSE_FILE}" "$@"
  elif command -v docker-compose >/dev/null 2>&1; then
    docker-compose -f "${COMPOSE_FILE}" "$@"
  else
    err "Neither \`docker compose\` nor \`docker-compose\` is available."
    return 1
  fi
}

start_compose_db() {
  if [[ ! -f "${COMPOSE_FILE}" ]]; then
    err "Compose file not found: ${COMPOSE_FILE}"
    return 1
  fi
  info "Starting PostgreSQL container (docker compose up -d ${COMPOSE_DB_SERVICE})..."
  if ! compose_cmd up -d "${COMPOSE_DB_SERVICE}"; then
    err "Failed to start compose service '${COMPOSE_DB_SERVICE}'."
    return 1
  fi
  return 0
}

# Ensure Docker is up, then make DATABASE_URL host:port reachable (start compose db if needed).
ensure_database_ready() {
  ensure_docker_ready
  load_database_url_from_env

  if database_reachable; then
    ok "PostgreSQL reachable at ${DB_HOST}:${DB_PORT}"
    ok "Database matches DATABASE_URL"
    return 0
  fi

  if db_host_is_local; then
    if ! start_compose_db; then
      print_database_diagnostics
      exit 1
    fi
  else
    err "PostgreSQL is not reachable at ${DB_HOST}:${DB_PORT}."
    info "Host is not local — not starting docker compose db automatically."
    print_database_diagnostics
    exit 1
  fi

  info "Waiting for PostgreSQL..."
  if wait_until "${POSTGRES_WAIT_TIMEOUT_S}" "Waiting for PostgreSQL" database_reachable; then
    ok "PostgreSQL ready"
    ok "PostgreSQL reachable at ${DB_HOST}:${DB_PORT}"
    ok "Database matches DATABASE_URL"
    return 0
  fi

  err "PostgreSQL did not become ready at ${DB_HOST}:${DB_PORT} within ${POSTGRES_WAIT_TIMEOUT_S}s."
  info "Check: docker compose -f docker-compose.yml ps db"
  info "Logs:  docker compose -f docker-compose.yml logs db --tail 50"
  print_database_diagnostics
  exit 1
}

# Status helper: Running | Stopped | Unknown based on DATABASE_URL (not brew/any PG).
postgres_status() {
  if [[ ! -f "${API_ENV_FILE}" ]]; then
    echo "Unknown"
    return 0
  fi
  local url
  if ! url="$(read_env_value "${API_ENV_FILE}" "DATABASE_URL")"; then
    echo "Unknown"
    return 0
  fi
  if ! parse_database_url "${url}"; then
    echo "Unknown"
    return 0
  fi
  if database_reachable; then
    echo "Running"
  else
    echo "Stopped"
  fi
}

print_postgres_line() {
  # Backward-compatible alias; prefer ensure_database_ready in start-dev.
  ensure_database_ready
}

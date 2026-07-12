# Scripts

Developer and CI helper scripts for SitePilot AI.

| Script | Responsibility |
|--------|----------------|
| `start-dev.sh` | Start API + web, wait for health, open browser |
| `stop-dev.sh` | Gracefully stop API + web (PID files) |
| `status.sh` | Show backend / frontend / PostgreSQL status |
| `setup.sh` | Bootstrap local environment |
| `run-web.sh` | Start the web app only |
| `run-api.sh` | Start the API app only |
| `lint.sh` | Run lint across the monorepo |
| `format.sh` | Run formatters across the monorepo |
| `lib/dev-common.sh` | Shared helpers for the `*-dev` / `status` scripts (Docker + DATABASE_URL checks) |

## Local stack

```bash
./scripts/start-dev.sh
./scripts/status.sh
./scripts/stop-dev.sh
```

`start-dev.sh` ensures Docker is running (launches Docker Desktop on macOS when needed),
reads `DATABASE_URL` from `apps/api/.env`, and starts `docker compose up -d db` if that
host:port is not reachable.

- Backend: `http://localhost:8000` (logs → `logs/api.log`)
- Frontend: `http://localhost:5173` (logs → `logs/web.log`)
- Make scripts executable if needed: `chmod +x scripts/*.sh scripts/lib/*.sh`

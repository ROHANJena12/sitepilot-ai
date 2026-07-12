# SitePilot AI — apps/api

**Responsibility:** FastAPI backend for SitePilot AI (`ARCHITECTURE.md` §6, `DATABASE_SPEC.md` §33).

## Sprint status

**Sprint 1:** foundation (FastAPI, settings, logging, health, Alembic env)  
**Sprint 2:** core domain persistence — `Organization`, `Project`, `Website`

Not included yet: auth, APIs for orgs/projects/websites, engines, crawling, AI.

## Local development

```bash
cd apps/api
python -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
cp .env.example .env

# optional: start Postgres + Redis from repo root
# docker compose up -d db redis

uvicorn app.main:app --reload --port 8000
```

Or from repo root:

```bash
./scripts/run-api.sh
```

### AI job queue

- Default: `AI_QUEUE_BACKEND=inmemory` (FastAPI `BackgroundTasks`, no Redis required)
- Distributed: `AI_QUEUE_BACKEND=redis` + `python -m app.ai.jobs.worker_main`
- See `.env.example` for `REDIS_URL`, `QUEUE_NAME`, `VISIBILITY_TIMEOUT`, etc.

## Health

```bash
curl http://localhost:8000/health
```

## Tests

```bash
cd apps/api
pytest
```

## Alembic

Configured against `app.db.base.Base` metadata. No domain migrations in Sprint 1.

```bash
alembic revision --autogenerate -m "message"   # after models exist
alembic upgrade head
```

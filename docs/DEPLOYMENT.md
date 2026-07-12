# SitePilot AI — Production Deployment

**Your AI-powered Website Intelligence Platform.**

This guide covers deploying the API and web app for production. It does not change product architecture — it documents operational setup for Sprint 35 readiness.

---

## Architecture (deployed)

| Component | Role |
|-----------|------|
| `apps/web` | Next.js frontend (static/SSR) |
| `apps/api` | FastAPI API + in-process audit/AI workers |
| PostgreSQL 16 | System of record |
| Redis 7 (optional) | Required when `AI_QUEUE_BACKEND=redis` |

---

## Required environment (API)

| Variable | Required in production | Notes |
|----------|------------------------|-------|
| `ENVIRONMENT` | Yes | Must be `production` |
| `SECRET_KEY` | Yes | Strong unique value — never the default placeholder |
| `DATABASE_URL` | Yes | `postgresql+asyncpg://…` (not localhost) |
| `PUBLIC_WEB_URL` | Yes | `https://…` origin for share links |
| `CORS_ORIGINS` | Yes | Comma-separated frontend origins |
| `GEMINI_API_KEY` | When default provider is Gemini | Fail-fast at startup |
| `OPENROUTER_API_KEY` / `OPENAI_API_KEY` | When selected as default | Fail-fast at startup |
| `REDIS_URL` | When `AI_QUEUE_BACKEND=redis` | Also used by `/ready` if required |
| `DEBUG` | Must be `false` | Enforced in production validation |
| `SECURITY_HEADERS_ENABLED` | Recommended `true` | Default on |
| `SECURITY_ENABLE_HSTS` | Auto-on in production | Or set explicitly |
| `RATE_LIMIT_ENABLED` | Recommended `true` | Default on |
| `READY_REQUIRE_REDIS` | Optional | Force Redis check on `/ready` |

Templates: `apps/api/.env.example`, root `.env.example`.

Startup validation (`app/core/startup.py`) **fails fast** on insecure production settings.

---

## Security headers

### API

`SecurityHeadersMiddleware` sets:

- `Content-Security-Policy` (API default is restrictive)
- `Referrer-Policy`
- `X-Content-Type-Options: nosniff`
- `X-Frame-Options`
- `Permissions-Policy`
- `Strict-Transport-Security` (production / when enabled)

Configurable via `SECURITY_*` env vars.

### Web

`apps/web/next.config.ts` applies browser security headers on all routes. HSTS only when `NODE_ENV=production`.

---

## Rate limiting

In-memory sliding windows (single API process):

| Endpoint class | Default |
|----------------|---------|
| `POST /api/v1/audits` | 5 / 10 minutes / IP |
| AI generate/regenerate | 30 / 60 seconds / IP |
| `POST /api/v1/audits/{id}/share` | 20 / 10 minutes / IP |

Responses use `429` + `RATE_LIMITED` + `Retry-After` / `X-RateLimit-*`.

For multi-replica deployments, front with an edge rate limiter (CDN / Nginx / API gateway) or replace the in-memory store with Redis.

---

## Health & readiness

| Path | Purpose |
|------|---------|
| `GET /health` and `GET /api/v1/health` | Liveness — version, uptime (no dependency I/O) |
| `GET /ready` and `GET /api/v1/ready` | Readiness — Postgres required; Redis when configured/required; provider key presence (non-blocking) |

Use `/health` for container `HEALTHCHECK`. Use `/ready` for load balancer admission.

---

## Docker

Build the API image:

```bash
docker build -t sitepilot-api:latest ./apps/api
```

Local stack (DB + Redis + API profile):

```bash
docker compose --profile api up --build
```

Compose sets `restart: unless-stopped` and service healthchecks. Prefer mounting secrets via a real `.env` (never commit production secrets).

---

## Web deployment

```bash
pnpm install
pnpm --filter @sitepilot/web build
pnpm --filter @sitepilot/web start
```

Set `NEXT_PUBLIC_API_URL` to the public API base (e.g. `https://api.example.com/api/v1`).

---

## CI

GitHub Actions (`.github/workflows/ci.yml`) runs:

1. API — Ruff + Pytest (Postgres service)
2. Web — typecheck, lint, build

---

## Logging

Structured logs (JSON in production) include `request_id`, `duration_ms`, `status_code`, and `error_code` on failed requests. Background audits log `audit_id` + duration.

**Never log:** API keys, `SECRET_KEY`, raw prompts, or Authorization headers.

---

## Checklist before go-live

- [ ] `ENVIRONMENT=production`, `DEBUG=false`
- [ ] Strong `SECRET_KEY`
- [ ] Production `DATABASE_URL` + migrations applied
- [ ] HTTPS termination + HSTS
- [ ] CORS locked to real origins
- [ ] Provider keys present for the default cascade
- [ ] `/health` and `/ready` wired in orchestrator
- [ ] Rate limits reviewed for expected traffic
- [ ] Secrets not in images or git

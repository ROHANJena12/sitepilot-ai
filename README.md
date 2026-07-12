# SitePilot AI

**Your AI-powered Website Intelligence Platform.**

---

## Vision

SitePilot AI helps teams understand, optimize, and govern their websites with AI.  
It turns crawl data, performance signals, SEO insights, and content intelligence into actionable recommendations — so product, marketing, and engineering can ship better web experiences faster.

This repository is an enterprise monorepo scaffold (Turborepo + pnpm workspaces), structured for production SaaS delivery similar to platforms like Vercel, Stripe, and Linear.

---

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                         apps/                               │
│              web (Next.js)  ·  api (FastAPI)                │
└───────────────────────────┬─────────────────────────────────┘
                            │
┌───────────────────────────▼─────────────────────────────────┐
│                       packages/                             │
│         ui · types · config · utils  (shared libs)          │
└───────────────────────────┬─────────────────────────────────┘
                            │
┌───────────────────────────▼─────────────────────────────────┐
│   infrastructure/   ·   docs/   ·   scripts/   ·   assets/   │
└─────────────────────────────────────────────────────────────┘
```

| Layer | Responsibility |
|-------|----------------|
| `apps/web` | Customer-facing web application |
| `apps/api` | Backend API and service layer |
| `packages/*` | Shared libraries consumed by apps |
| `infrastructure/` | Docker, Nginx, Terraform definitions |
| `docs/` | Product, architecture, and process docs |
| `scripts/` | Developer and CI helper scripts |

---

## Folder Structure

```
sitepilot-ai/
├── apps/                  # Deployable applications
│   ├── web/               # Frontend (Next.js) — placeholder
│   └── api/               # Backend (FastAPI) — placeholder
├── packages/              # Shared internal packages
│   ├── ui/                # Design system / UI primitives
│   ├── types/             # Shared TypeScript / schema types
│   ├── config/            # Shared tooling & runtime config
│   └── utils/             # Shared utilities
├── docs/                  # Product & engineering documentation
├── infrastructure/        # Docker, Nginx, Terraform
├── scripts/               # Setup, run, lint, format helpers
├── assets/                # Brand logos, icons, images, mockups
├── .github/workflows/     # CI and release pipelines
├── package.json           # Root workspace manifest
├── turbo.json             # Turborepo pipeline config
├── pnpm-workspace.yaml    # pnpm workspace definition
├── docker-compose.yml     # Local multi-service orchestration
├── .env.example           # Environment variable template
├── LICENSE                # MIT
└── README.md              # This file
```

---

## Local Development

One-command local stack (API + web):

```bash
./scripts/start-dev.sh
```

Check status:

```bash
./scripts/status.sh
```

Stop everything:

```bash
./scripts/stop-dev.sh
```

| Service | URL |
|---------|-----|
| Backend (FastAPI) | http://localhost:8000 |
| Frontend (Next.js) | http://localhost:5173 |
| API health | http://localhost:8000/health |

Logs: `logs/api.log`, `logs/web.log`. PIDs: `.pids/api.pid`, `.pids/web.pid`.

**Prerequisites:** `apps/api/.venv`, frontend `node_modules` (`npm install` / `pnpm install`), and preferably `apps/api/.env` (copied from `.env.example`). PostgreSQL is detected when present but is not required for the script to start.

**Report export (Sprint 30):** from a completed audit report page, use **Export → PDF / JSON / CSV**, or call `GET /api/v1/audits/{audit_id}/export/{pdf|json|csv}` for an immediate file download. See [`docs/REPORT_COMPOSER.md`](./docs/REPORT_COMPOSER.md).

**Report sharing (Sprint 31):** from a completed report, use **Share → Copy Link / Open in New Tab** (or native share on mobile). Creates a signed URL `/share/{token}` that opens the same `ReportDashboard` in **read-only** mode (no AI, export, or regenerate). API: `POST /api/v1/audits/{audit_id}/share`, `GET /api/v1/share/{token}`.

**Public pages (Sprint 32):** marketing and legal surfaces live under `apps/web` only — `/about`, `/contact`, `/help`, `/faq`, `/privacy`, `/terms` (plus `/docs` → `/help`). Nav: About · Help · Contact. Footer includes Privacy, Terms, GitHub, LinkedIn, and Contact.

**QA polish (Sprint 33):** analyzing flow is idempotent on refresh/back (session locks + `replace` to report); sample report preview at `/report/demo`; FAQ deep links open the matching accordion; AI generate shows live job progress; shared report errors include Home / New audit escapes.

**Performance (Sprint 34):** `POST /audits` returns quickly with `pending`; the analyzing page polls `GET /audits/{id}` for live `progress` / `current_engine` (no fake timer). AI job polling uses adaptive intervals (500ms → 1s → 2s). Report charts are code-split.

**Production readiness (Sprint 35):** security headers, startup env validation, IP rate limits on audit/AI/share, `/health` + `/ready`, structured request logging, multi-stage API Docker image, and CI (pytest + web typecheck/lint/build). See [`docs/DEPLOYMENT.md`](./docs/DEPLOYMENT.md) and [`docs/SECURITY.md`](./docs/SECURITY.md).

---

## Development Workflow

Local MVP path (Sprint 28–29):

1. **Copy** `apps/api/.env.example` → `apps/api/.env` (set `GEMINI_API_KEY` / `AI_DEFAULT_PROVIDER=gemini`; OpenRouter/OpenAI keys optional for fallback).
2. **Postgres** on `:5434`, optional **Redis** on `:6379` (`docker compose up -d` if used).
3. **Preferred:** `./scripts/start-dev.sh` (or start API/web manually below).
4. **API (manual):** `cd apps/api && uvicorn app.main:app --reload --port 8000`
5. **Web (manual):** `pnpm --filter @sitepilot/web dev` (`NEXT_PUBLIC_API_URL=http://localhost:8000/api/v1`; package default port is 3000 — `start-dev.sh` uses 5173)
6. **E2E harness:** `apps/api/.venv/bin/python docs/sprint29_e2e.py`
7. **Integration report:** `docs/SPRINT29_INTEGRATION_REPORT.md`
8. **Lint / format** via `scripts/lint.sh` and `scripts/format.sh`.
9. **Ship** through [`.github/workflows/ci.yml`](./.github/workflows/ci.yml) (API pytest + web typecheck/lint/build).
10. **Production:** follow [`docs/DEPLOYMENT.md`](./docs/DEPLOYMENT.md).

Helper scripts live under [`scripts/`](./scripts/README.md).

---

## Roadmap

See [`docs/ROADMAP.md`](./docs/ROADMAP.md) for phased delivery. High-level:

| Phase | Focus |
|-------|--------|
| 0 | Monorepo scaffold & documentation (current) |
| 1 | Core API + web shell |
| 2 | Crawl & intelligence pipelines |
| 3 | Insights UI & reporting |
| 4 | Billing, auth, multi-tenant hardening |

---

## Tech Stack

| Area | Choice |
|------|--------|
| Monorepo | Turborepo + pnpm workspaces |
| Web | Next.js (planned) |
| API | FastAPI (planned) |
| Types | Shared `packages/types` |
| UI | Shared `packages/ui` |
| Infra | Docker, Nginx, Terraform |
| CI/CD | GitHub Actions |
| AI | OpenAI, Gemini (keys via env) |
| Data | PostgreSQL, Redis (planned) |

---

## Documentation

| Document | Description |
|----------|-------------|
| [PRD](./docs/PRD.md) | Product requirements |
| [Architecture](./docs/ARCHITECTURE.md) | System design |
| [API Spec](./docs/API_SPEC.md) | API contract outline |
| [UI Guidelines](./docs/UI_GUIDELINES.md) | Design standards |
| [Contributing](./docs/CONTRIBUTING.md) | Contribution guide |
| [Security](./docs/SECURITY.md) | Security practices |
| [Changelog](./docs/CHANGELOG.md) | Release history |

---

## License

MIT — see [LICENSE](./LICENSE).

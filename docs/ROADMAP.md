# Roadmap

**Product:** SitePilot AI  
**Last updated:** 2026-07-11

---

## Phase 0 — Scaffold (current)

- [x] Monorepo layout (apps, packages, docs, infra, scripts)
- [x] Root tooling manifests (pnpm, Turbo, Docker Compose)
- [x] Documentation set
- [x] CI / release workflow placeholders

## Phase 1 — Foundations

- [ ] `apps/api` skeleton (FastAPI app entry, health route)
- [ ] `apps/web` skeleton (Next.js shell)
- [ ] Shared packages wired (`types`, `config`, `utils`)
- [ ] Local Docker Postgres + Redis
- [ ] Auth strategy decision

## Phase 2 — Intelligence core

- [ ] Site registration & ownership verification
- [ ] Crawl / fetch pipeline (bounded)
- [ ] PageSpeed + AI insight generation
- [ ] Persist audits & insights

## Phase 3 — Product surface

- [ ] Dashboard UX
- [ ] Insight prioritization & status workflow
- [ ] Reports / export
- [ ] `packages/ui` design system v1

## Phase 4 — SaaS hardening

- [ ] Billing & plans
- [ ] Multi-tenant quotas
- [ ] Observability & SLOs
- [ ] Production Terraform modules
- [ ] Public API keys & webhooks

## Phase 5 — Scale & ecosystem

- [ ] Advanced scheduling & workers
- [ ] Integrations marketplace
- [ ] Team collaboration features
- [ ] Regional data residency options

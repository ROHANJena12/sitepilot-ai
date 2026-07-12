---
description: Global SitePilot AI engineering rules — documentation-first workflow, architecture, and quality gates
alwaysApply: true
---

# SitePilot AI — Global Engineering Rules

These rules apply to **every** implementation task in this repository.

## Single Source of Truth (Documentation First)

Before writing code, read the relevant specs. Never contradict them. If docs conflict, **stop**, explain the conflict, and wait for direction.

| Document | Authority |
|---|---|
| `docs/PRD.md` | Product requirements |
| `docs/ENGINE_SPEC.md` | Engine contracts & pipeline |
| `docs/DATABASE_SPEC.md` | PostgreSQL schema (system of record) |
| `docs/DOMAIN_MODEL.md` | Ubiquitous language, DDD boundaries |
| `docs/GRAPH_ARCHITECTURE_SPEC.md` | Neo4j projection (derived, not SoR) |
| `docs/API_SPEC.md` | REST / OpenAPI contracts |
| `docs/ARCHITECTURE.md` | Master system architecture |
| `docs/UI_SCREEN_SPEC.md` | Screens, journeys, UX |
| `docs/DESIGN_SYSTEM.md` | Tokens, components, themes |

**Documentation-first means:** inspect docs → compare to repo → plan → implement approved changes only.

---

## 1. Documentation First

- Always inspect documentation before writing code.
- Never contradict project documentation.
- If documentation conflicts exist, explain them before implementing.
- Prefer updating docs in the same PR when behavior intentionally changes (via explicit request).

---

## 2. Repository Inspection

Before every implementation:

1. Inspect the existing project structure and related files.
2. Identify what already exists vs what is missing.
3. Never recreate files unnecessarily.
4. Extend existing code instead of replacing it.
5. Do not delete or rewrite scaffolds unless required for the task.

---

## 3. Development Workflow

Always follow this sequence:

1. Inspect repository.
2. Read relevant documentation.
3. Compare implementation with documentation.
4. Explain findings (what exists / gaps / conflicts).
5. Create an implementation plan.
6. Implement only approved / requested changes.
7. Explain modified files.
8. Verify the project still builds (and lint/types where tooling exists).

Do not skip planning when the change spans multiple layers (API + DB + UI + engines).

---

## 4. Engineering Principles

Follow:

- **SOLID** — especially single responsibility for engines and modules
- **DRY** — no duplicated business rules across UI, API, and prompts
- **KISS** — simplest maintainable solution
- **Clean Architecture** — domain/application inward; infrastructure at edges
- **Domain-Driven Design** — use DOMAIN_MODEL ubiquitous language (`Audit Run`, `Finding`, `Recommendation`, etc.)
- **Feature-Sliced Design (Frontend)** — `app → widgets → features → entities → shared`

Prefer composition over inheritance. Write reusable code. Avoid duplication.

---

## 5. Frontend Standards

Stack:

- Next.js (App Router)
- TypeScript
- Tailwind CSS
- shadcn/ui (restyled to SitePilot tokens — not default look)
- Framer Motion
- Lucide React

Rules:

- Never hardcode colors, spacing, or radii — use design tokens from `DESIGN_SYSTEM.md`.
- Follow `DESIGN_SYSTEM.md` and `UI_SCREEN_SPEC.md`.
- Keep route `page.tsx` files thin composition shells.
- Do not recompute Health Scores or invent Findings in the client — render API report truth.
- Respect accessibility (WCAG 2.2 AA) and `prefers-reduced-motion`.

FSD layout lives under `apps/web/` (`app/`, `features/`, `entities/`, `widgets/`, `shared/`).

---

## 6. Backend Standards

Stack:

- FastAPI
- SQLAlchemy
- Alembic
- PostgreSQL
- Pydantic

Rules:

- Keep business logic out of API routes (routers → use-cases/domain/engines).
- Prefer dependency injection.
- Use async where appropriate (I/O-bound work).
- Engines expose typed `run(ctx, input) -> output` contracts; no sibling engine imports.
- AI must only consume Data Quality payloads — never invent Findings.

---

## 7. Database Standards

- **PostgreSQL is the source of truth.**
- Follow `DATABASE_SPEC.md` exactly.
- Do not invent schema, tables, or columns not in the spec (propose doc updates first if needed).
- Neo4j (if used) is a **derived projection** — sync from Postgres; never SoR for audits/billing/secrets.
- Use Alembic for all schema changes; no manual prod DDL.

---

## 8. API Standards

- Follow `API_SPEC.md` (resource paths, status codes, error envelope).
- Use consistent response models.
- Validate all inputs (Pydantic; `extra=forbid` on public bodies where specified).
- Use proper HTTP status codes (`202` for async audit accept, etc.).
- Document public APIs (OpenAPI via FastAPI models).
- Prefer canonical `/api/v1/audits` resources; keep PRD aliases only if specified.

---

## 9. Architecture Standards

Follow `ARCHITECTURE.md` and `ENGINE_SPEC.md`.

Every engine must:

- Have a **single responsibility**
- Be **independently testable**
- Communicate through **well-defined contracts**
- Be **replaceable** without breaking siblings
- Emit structured logs with `audit_id` / `trace_id`

MVP shape: modular monolith (API + workers), not premature microservices.

---

## 10. UI Standards

Follow `DESIGN_SYSTEM.md` and `UI_SCREEN_SPEC.md`.

Maintain:

- Consistent spacing, typography, colors (tokens only)
- Shared component patterns (`IssueCard`, `HealthScoreRing`, etc.)
- Accessibility and responsive breakpoints
- Motion per design tokens (calm, professional — no confetti/glow spam)
- Dark-first app theme with light twin support

Marketing: brand-first hero; no cards/overlays in the hero unless the screen spec explicitly allows.

---

## 11. Code Review Checklist

Before considering any task complete, verify:

- [ ] Code matches documentation
- [ ] No duplicate functionality
- [ ] No unnecessary files created
- [ ] No broken imports
- [ ] Type safety maintained
- [ ] Lint passes (when configured)
- [ ] Build passes (when configured)
- [ ] Architecture remains consistent (FSD / Clean / engine boundaries)
- [ ] No secrets committed
- [ ] Domain language used correctly

---

## 12. General Rules

- If implementation is ambiguous: **never guess**. Explain ambiguity; propose the most maintainable option.
- Quality is more important than speed.
- Do not implement UI/business logic when the task asks for architecture/docs/placeholders only.
- Do not expand scope beyond the request.
- Prefer small, reviewable diffs.

### Ubiquitous Language (quick reference)

Use: **Audit Run**, **Finding**, **Recommendation**, **Health Score**, **Confidence Score**, **Engine**, **Organization**, **Project**, **Website**, **Report**.

Avoid ambiguous synonyms in code/docs (`scan`/`job` without mapping to Audit Run or Engine Execution).

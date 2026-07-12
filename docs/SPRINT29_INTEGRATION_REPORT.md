# Sprint 29 — End-to-End Integration Report

**Date:** 2026-07-12  
**Scope:** Integration validation only (no architecture redesign)  
**Evidence:** `docs/sprint29_evidence.json`, harness `docs/sprint29_e2e.py`  
**Unit suite:** 626 passed

---

## Verdict

The SitePilot happy path is executable from UI → API → pipeline → report → AI (OpenRouter) → async jobs → persistence. Integration bugs found during live validation were fixed. Remaining gaps are **model-quality / grounding** on free OpenRouter models and a few **documented MVP limitations** (no `/ready`, no `audit_pages` table).

---

## Working flows

| Flow | Result | Notes |
|------|--------|-------|
| Health | Pass | `GET /health` |
| Create website | Pass | `POST /websites` → default org/project |
| Sync audit | Pass | ~1.5–3s for example.com; engines + health + recommendations |
| Report | Pass | Score/grade, findings, recs, quick wins, `resource_id` present |
| DB integrity | Pass | `audit_runs`, `engine_executions`, `audit_findings`, `recommendations`, `reports`, `health_scores`; no orphans |
| AI sync finding | Pass | OpenRouter `openai/gpt-oss-120b:free`, grounded, `X-AI-*` headers |
| AI async recommendation | Pass* | Job runs; free model may return empty JSON (VALIDATION) |
| AI async executive | Pass* | Job runs; free model often fails grounding |
| AI async business | Pass* | Job runs after drain fix; grounding may reject invented positives |
| AI async quick win | Pass | |
| AI versions / regen / latest | Pass | |
| AI cancel | Pass | Body field `reason` |
| Error contracts | Pass | 404 missing report, 400 bad URL |
| Frontend pages | Pass | `/`, `/audit`, `/report/{auditId}` return 200 |
| Unit tests | Pass | 626 |

\* Executive may complete as `failed` with `VALIDATION` when the free model invents scores — grounding is correctly rejecting hallucinations.

---

## Broken / limited flows (documented)

| Item | Status | Root cause | Action |
|------|--------|------------|--------|
| `GET /ready` | 404 | Not implemented (liveness only) | Future sprint |
| `audit_pages` table | N/A | Not in current schema; crawl pages not separately persisted | Spec debt — not a regression |
| Free-model grounding | Intermittent VALIDATION | Model invents scores / positives | Use stronger model or retries later |
| Audit create DTO | OK | Returns `{audit_id,status,message}` not full poll DTO | FE already uses `audit_id` |

---

## Integration bugs fixed this sprint

1. **CORS `.env` boot failure** — comma-separated `CORS_ORIGINS` failed pydantic-settings JSON decode → `NoDecode` + parser (`app/core/config.py`).
2. **FE cancel body** — sent `cancel_reason`; API expects `reason` (`apps/web/shared/services/ai.service.ts`).
3. **CORS expose headers** — added `X-Generation-ID` / `X-AI-*` (`app/main.py`).
4. **OpenRouter empty payload** — `chat.completions.parse` returned 200 with `parsed=None`/`content=None` and never fell through to `json_object`; also strip markdown fences; catch `ValidationError` on Responses parse (`openrouter_provider.py`, `structured_output.py`).
5. **In-memory jobs stuck queued** — single `process_next` + mid-drain enqueue race + BackgroundTasks delay → drain-until-empty, `_DRAIN_NEEDED` continuation, single-flight schedule via `asyncio.create_task`, poll kick (`dependencies/ai_jobs.py`, `api/v1/ai/jobs.py`, `enqueue.py`).
6. **Local `.env` leaking into unit tests** — skip dotenv under `SITEPILOT_TESTING` (`settings_sources.py` + conftest).

---

## Architecture validation

| Subsystem | Integrates? |
|-----------|-------------|
| Website bootstrap | Yes |
| Audit pipeline (sync in-request) | Yes |
| Engines → findings / health / recommendations | Yes |
| Report composer + FE mapper (`resource_id`) | Yes |
| AIService + grounding + cache + persistence | Yes |
| `AIProvider` / OpenRouter selection via env | Yes |
| Async jobs (inmemory BackgroundTasks) | Yes (after drain fix) |
| Versioning / regenerate / cancel | Yes |
| Frontend audit → analyzing → report | Yes (sync POST path) |

**Not redesigned:** pipeline, engines, grounding, builders, cache keys, DB schema, job API contracts.

---

## Performance snapshot (live example.com)

| Step | Typical ms |
|------|------------|
| Create website | ~80–100 |
| Audit | ~1.5–3k |
| Report | ~50–100 |
| AI sync finding | ~11–18k |
| AI async recommendation | ~25k |
| AI async executive | ~25–60k |
| AI async business | ~29k |

Bottlenecks: OpenRouter free-model latency; sync audit still blocks the HTTP request (by design for MVP).

---

## Future sprints (do not implement here)

- Implement `GET /ready` (DB + Redis)
- Persist crawl pages if product requires `audit_pages`
- Stronger default model / retry-on-VALIDATION for free-tier flakiness
- Async audit (`202`) instead of sync POST
- Auth

---

## How to re-validate

```bash
# API (from apps/api, loads .env with OpenRouter)
uvicorn app.main:app --port 8000

# Web
pnpm --filter @sitepilot/web dev

# Live harness
apps/api/.venv/bin/python docs/sprint29_e2e.py

# Unit suite
cd apps/api && .venv/bin/pytest -q
```

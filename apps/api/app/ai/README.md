# SitePilot AI Foundation (`app/ai/`)

OpenAI explanations for Findings, Recommendations, Executive Summaries,
Business Summaries, and Quick Wins.
AI explains completed audit artifacts — it never invents scores, findings,
or recommendations, and never estimates confidence.

## Runtime architecture

```
Mapper
   ↓
Builder
   ↓
BuiltPrompt          (+ prompt_hash, PromptDiagnostics, AIFeature)
   ↓
GenerationRequest / GenerationSession
   ↓
generation_id        (minted once in GenerationSession.start())
   ↓
Cache                (content keys — never include generation_id)
   ↓
Provider
   ↓
Grounding
   ↓
AIQualityMetadata
   ↓
AIResponse[T]
```

## HTTP API (Sprint 23–27)

REST routers are orchestration only. They never construct prompts, call OpenAI,
or skip grounding:

```
API → Application Use Case → AIService → (architecture above) → AIResponse[T]
                                    ↓
                              Persist / regenerate

API → QueueGenerationUseCase → QueuePort → 202 job_id
         InMemoryQueue (default)     RedisQueue
              ↓                           ↓
    BackgroundTasks worker         RedisWorker process
```

Layout:

```
app/api/v1/ai/
  findings.py          # explain, generate(async), regenerate, latest, versions
  recommendations.py   # explanation + quick-win (+ async/regen/history)
  reports.py           # executive + business (+ async/regen/history)
  jobs.py              # poll / result / cancel / list
  enqueue.py           # shared 202 helper
  errors.py            # HTTP mapping
  response.py          # AIResponse → JSON + X-AI-* headers

app/ai/jobs/
  queue.py             # QueuePort + InMemoryQueue + QueueDiagnostics
  redis_queue.py       # RedisQueue
  redis_worker.py      # RedisWorker
  factory.py           # create_job_queue
  worker.py            # in-process BackgroundWorker
  worker_main.py       # python -m app.ai.jobs.worker_main
  status.py            # JobStatus

app/application/ai/jobs/
  queue_generation.py
  process_generation_job.py
  get_generation_job.py
  get_job_result.py
  list_generation_jobs.py
  cancel_generation_job.py
```

| Endpoint | Feature | operationId |
|---|---|---|
| `GET /api/v1/audits/{audit_id}/ai/executive-summary` | Executive Summary | `getAuditAiExecutiveSummary` |
| `GET /api/v1/audits/{audit_id}/ai/business-summary` | Business Summary | `getAuditAiBusinessSummary` |
| `GET /api/v1/findings/{finding_id}/ai/explanation` | Finding Explanation | `getFindingAiExplanation` |
| `GET /api/v1/recommendations/{recommendation_id}/ai/explanation` | Recommendation Explanation | `getRecommendationAiExplanation` |
| `GET /api/v1/recommendations/{recommendation_id}/ai/quick-win` | Quick Win Explanation | `getRecommendationAiQuickWin` |
| `POST …/ai/generate*` | Async enqueue (`202`) | see OpenAPI |
| `GET /api/v1/jobs/{job_id}` | Poll job | `getAiGenerationJob` |
| `GET /api/v1/jobs/{job_id}/result` | Completed AIResponse | `getAiGenerationJobResult` |
| `POST …/ai/regenerate*` | Controlled regeneration | see OpenAPI |
| `GET …/ai/latest` (or `…/{feature}/latest`) | Highest version | — |
| `GET …/ai/versions` | History metadata | — |
| `GET …/ai/versions/{version}` | Stored AIResponse | — |

OpenAPI tag: **`AI`**. Successful responses include headers `X-Generation-ID`,
`X-AI-Provider`, `X-AI-Model`, `X-AI-Cached`, `X-AI-Feature` (copied from
`AIResponse`; JSON body unchanged).

Finding / recommendation path IDs are **persisted row UUIDs**
(`audit_findings.id` / `recommendations.id`). HTTP responses are live
`AIResponse[T]`. After grounding, use cases best-effort persist immutable
rows to `ai_generations` (see DATABASE_SPEC §16A) — storage failures never
fail the API. Cache hits remain automatic via `AIService` / `GenerationSession`.

## Async jobs (Sprint 26–27)

```
POST …/generate → QueueGenerationUseCase → ai_generation_jobs + QueuePort.enqueue
        ↓
InMemory: BackgroundWorker.process_next()   |   Redis: RedisWorker loop
        ↓
AIJobRunner (progress + phase_history) → existing Generate*UseCase
        ↓
ack → job.status = completed | failed
```

- Queue: `QueuePort` → `InMemoryQueue` (default) or `RedisQueue` via `AI_QUEUE_BACKEND`
- Redis worker: `python -m app.ai.jobs.worker_main` (requires `AI_QUEUE_BACKEND=redis`)
- Visibility timeout + per-job Redis lock → crash reclaim; `ack` after run
- Config: `REDIS_URL`, `QUEUE_NAME`, `VISIBILITY_TIMEOUT`, `WORKER_POLL_INTERVAL`, `MAX_CONCURRENT_WORKERS`
- Worker identity: `DEFAULT_WORKER_ID` = `local-worker-1` (centralized in `app/ai/jobs/identity.py`)
- Progress: 0 → 10 → 20 → 40 → 70 → 90 → 100 (failed/cancelled keep current)
- Phase history: JSONB checkpoints with `duration_ms` (informational)
- Timing: `queued_at` / `started_at` / `completed_at` persisted; durations derived
- Failure category: `JobFailureCategory` on failed/cancelled jobs
- Events / summary / health: derived for poll DTO (not separate tables)
- Provider diagnostics: mirrored from stored `AIResponse` metadata
- Lifecycle (26.3): `expires_at` on completed (+24h); `expired` / `cleanup_candidate` / `stale` / `age_ms` / `duration_class` / `queue_class` derived — **no row deletion**
- Retention constants: `JOB_RETENTION_*_DAYS` in `app/ai/jobs/retention.py`
- Retry metadata: `attempt`, `max_attempts`, `next_retry_at`, `last_error` (retry loop not implemented)
- Cancel: `cancel_reason` enum (`USER_REQUESTED`, `TIMEOUT`, …)
- Completed poll: `generation_id`, `latest_version`, `result_url`
- Poll: `GET /jobs/{id}`; result: `GET /jobs/{id}/result`
- Jobs table is separate from `ai_generations` (DATABASE_SPEC §16B)

## Persistence (Sprint 24) & regeneration (Sprint 25)

```
AIResponse (grounded)
        ↓
response_hash (SHA-256, volatile ids excluded)
        ↓
AIGenerationRepository.regenerate() / create_or_reuse()
        ↓
return original AIResponse
```

- Entity types: `AIEntityType` (`finding`, `recommendation`, …)
- Versioning: identical `(feature, entity_id, report_hash, response_hash)` reuses version; content change → `version + 1`
- Never updates or deletes prior rows
- `GET …/latest` → highest version for current report hash
- `GET …/versions` → `GenerationHistoryDTO` (metadata only)
- `GET …/versions/{n}` → stored `AIResponse`

See `docs/API_SPEC.md` §7A and `docs/DATABASE_SPEC.md` §16A.

## Supported generation

| AIFeature | Prompt id | Provider | entity_id |
|---|---|---|---|
| `FINDING` | `finding_explanation` | configured default | `finding_id` |
| `RECOMMENDATION` | `recommendation` | configured default | `recommendation_id` |
| `EXECUTIVE_SUMMARY` | `executive_summary` | configured default | `audit_id` |
| `BUSINESS_SUMMARY` | `business_summary` | configured default | `audit_id` |
| `QUICK_WIN` | `quick_win` | configured default | `recommendation_id` |

## Providers (Sprint 28.1–28.2)

Canonical identity is ``AIProvider`` (`providers/provider_enum.py`), a `StrEnum`
mirroring ``AIFeature``. Env vars and JSON still use string values
(`"openai"`, `"openrouter"`, …); `resolve_provider()` accepts either form.

`ProviderFactory` / `ProviderRegistry` are keyed by ``AIProvider``:

| AIProvider | Implementation | Notes |
|---|---|---|
| `GEMINI` (`gemini`) | `GeminiProvider` | **Default** — all features; model `gemini-3.1-flash-lite` |
| `OPENROUTER` (`openrouter`) | `OpenRouterProvider` | Fallback hop #2 |
| `OPENAI` (`openai`) | `OpenAIProvider` | Fallback hop #3 |
| `ANTHROPIC` (`anthropic`) | placeholder | |
| `OLLAMA` (`ollama`) | placeholder | |

Auto-routing chain (when `provider=` is not set):

```
Gemini → OpenRouter → OpenAI
```

Configure with env:

```bash
AI_DEFAULT_PROVIDER=gemini
GEMINI_API_KEY=...
GEMINI_MODEL=gemini-3.1-flash-lite
OPENROUTER_API_KEY=sk-or-...   # fallback
OPENAI_API_KEY=sk-...          # final fallback
```

`AI_DEFAULT_PROVIDER=gemini` resolves to `AIProvider.GEMINI` in settings.
Structured JSON parsing is shared in `providers/structured_output.py`.
Grounding remains in AIService and is provider-agnostic.

## Quick Win flow

```
RecommendationDTO
        ↓
QuickWinMapper
        ↓
QuickWinContext
        ↓
AIContext
        ↓
QuickWinBuilder
        ↓
GenerationRequest → GenerationSession → Cache → Provider (AIProvider.*)
        ↓
QuickWinGroundingValidator
        ↓
AIResponse[QuickWinExplanation]
```

Quick Wins are explanations only. The Recommendation Engine decides what is a
quick win; AI explains why — never invents or reorders recommendations.

## Traceability

`generation_id` identifies an execution. Cache keys identify content.
`AIFeature` is the canonical internal feature registry.
`AIProvider` is the canonical internal provider registry.

# SitePilot AI — API Specification

**Your AI-powered Website Intelligence Platform.**

| | |
|---|---|
| **Document Type** | REST API Specification (OpenAPI 3.1 aligned) |
| **Product** | SitePilot AI |
| **Document** | `API_SPEC.md` |
| **Version** | 1.0.0 |
| **API Version** | `v1` |
| **Status** | `Draft — API Contract Authority` |
| **Base URL (prod)** | `https://api.sitepilot.ai/api/v1` |
| **Base URL (local)** | `http://localhost:8000/api/v1` |
| **Framework** | FastAPI (Python) |
| **Owner** | Platform Engineering |
| **Audience** | Backend, Frontend, AI, QA, DevOps |
| **Last Updated** | 2026-07-12 |
| **Companion Docs** | [PRD.md](./PRD.md), [DOMAIN_MODEL.md](./DOMAIN_MODEL.md), [DATABASE_SPEC.md](./DATABASE_SPEC.md), [ENGINE_SPEC.md](./ENGINE_SPEC.md), [SECURITY.md](./SECURITY.md) |

> [!NOTE]
> This document is the **HTTP contract authority** for SitePilot AI. FastAPI routers, Pydantic models, frontend clients, and generated OpenAPI must conform. Spec changes require an RFC and a versioning decision (§16).

> [!WARNING]
> MVP may allow **anonymous audits** (rate-limited by IP). Authenticated multi-tenant routes still appear in this contract so V2 does not break clients. Where auth is optional, endpoints say so explicitly.

---

## Table of Contents

1. [API Overview](#1-api-overview)
2. [API Design Principles](#2-api-design-principles)
3. [Authentication](#3-authentication)
4. [API Resources](#4-api-resources)
5. [Endpoint Specification Template](#5-endpoint-specification-template)
6. [Audit Endpoints](#6-audit-endpoints)
7. [Report Endpoints](#7-report-endpoints)
8. [Engine Endpoints](#8-engine-endpoints)
9. [Finding & Recommendation Endpoints](#9-finding--recommendation-endpoints)
10. [Monitoring Endpoints](#10-monitoring-endpoints)
11. [User Endpoints](#11-user-endpoints)
12. [Organization, Project & Website Endpoints](#12-organization-project--website-endpoints)
13. [Subscription & API Key Endpoints](#13-subscription--api-key-endpoints)
14. [System Endpoints](#14-system-endpoints)
15. [Error Model](#15-error-model)
16. [Validation Rules](#16-validation-rules)
17. [OpenAPI Spec](#17-openapi-spec)
18. [API Sequence Diagrams](#18-api-sequence-diagrams)
19. [API Versioning Strategy](#19-api-versioning-strategy)
20. [Webhooks](#20-webhooks)
21. [Rate Limiting](#21-rate-limiting)
22. [Security](#22-security)
23. [Implementation Roadmap](#23-implementation-roadmap)

---

## 1. API Overview

### 1.1 Purpose

The SitePilot AI HTTP API enables clients to:

- Start and poll **Audit Runs** against public Websites
- Retrieve **Engine** outputs, **Findings**, **Recommendations**, and **Reports**
- Manage tenancy (**Organizations**, **Projects**, **Websites**) when authenticated
- Export PDFs, manage monitoring (future), subscriptions, and API keys

### 1.2 Architecture

```mermaid
flowchart LR
    FE[Next.js Frontend]
    CLI[API Clients / SDK]
    GW[TLS / Edge]
    API[FastAPI /api/v1]
    PG[(PostgreSQL)]
    RD[(Redis)]
    W[Workers]
    N4J[(Neo4j optional)]

    FE --> GW --> API
    CLI --> GW
    API --> PG
    API --> RD
    API --> W
    W --> PG
    W --> N4J
```

| Layer | Responsibility |
|---|---|
| FastAPI | Validation, authn/z, orchestration commands, read models |
| Workers | Engine pipeline (see ENGINE_SPEC) |
| PostgreSQL | System of record |
| Redis | Rate limits, cache, job queue |
| Neo4j | Optional insights (not on MVP critical path) |

### 1.3 Versioning Strategy

- URI versioning: `/api/v1/...`
- Breaking changes require `/api/v2` or negotiated compatibility headers
- Additive fields are non-breaking within `v1`

### 1.4 Naming Conventions

| Item | Convention | Example |
|---|---|---|
| Resources | plural nouns | `/audits`, `/websites` |
| Path params | `{id}` UUID | `/audits/{audit_id}` |
| Query params | `snake_case` | `?page_size=20` |
| JSON fields | `snake_case` | `health_score` |
| Headers | `X-Request-Id`, `Authorization` | |
| Errors | `UPPER_SNAKE` codes | `INVALID_URL` |

### 1.5 Resource Design

Resources map to [DOMAIN_MODEL.md](./DOMAIN_MODEL.md) aggregates:

`Organization` → `Project` → `Website` → `Audit` (Audit Run) → `Report`

### 1.6 Stateless Design

- No sticky sessions required for API nodes
- Auth via bearer JWT or API key on each request
- Audit progress via explicit status resources / polling (WebSocket optional later)

---

## 2. API Design Principles

| Principle | Application |
|---|---|
| **REST** | Resource URLs; proper verbs; HTTP semantics (`201` when the resource is created synchronously; `202` when work is accepted asynchronously) |
| **Idempotency** | `Idempotency-Key` on `POST /audits` and key creation; safe `GET`/`PUT` |
| **Pagination** | Cursor/keyset: `page_size`, `cursor` (prefer over `offset`) |
| **Filtering** | Query params: `status`, `website_id`, `priority` |
| **Sorting** | `sort=created_at:desc` |
| **Validation** | Pydantic request models; `422` with field errors |
| **Error Handling** | Standard envelope (§15) |
| **Rate Limiting** | Per IP / user / API key (§21) |
| **Versioning** | `/api/v1` (§19) |
| **JSON-first** | `application/json`; PDF via URL not multipart by default |
| **Async jobs** | Long-running pipeline work is intended to return `202` + pollable resource once a job queue is wired; today `POST /audits` creates the AuditRun synchronously (`201`) and clients poll `GET /audits/{id}` |

### 2.1 Common Headers

| Header | Required | Description |
|---|---|---|
| `Authorization` | Conditional | `Bearer <jwt>` or `Bearer <api_key>` |
| `Content-Type` | On bodies | `application/json` |
| `Accept` | Optional | `application/json` |
| `X-Request-Id` | Optional | Client correlation; echoed |
| `Idempotency-Key` | Recommended on POST audits | UUID/string ≤ 128 chars |

### 2.2 Common Response Headers

| Header | Description |
|---|---|
| `X-Request-Id` | Correlation id |
| `X-RateLimit-Limit` | Window limit |
| `X-RateLimit-Remaining` | Remaining |
| `X-RateLimit-Reset` | Unix reset time |
| `Retry-After` | Seconds (on 429) |

---

## 3. Authentication

### 3.1 Modes

| Mode | MVP | V2+ |
|---|---|---|
| Anonymous (IP rate-limited) | Yes — create/read audits by id | Limited |
| JWT Bearer | Optional scaffold | Primary user auth |
| API Keys | Enterprise scaffold | Programmatic access |
| OAuth 2.1 / OIDC | Future | SSO |

### 3.2 JWT

| Claim | Meaning |
|---|---|
| `sub` | `user_id` UUID |
| `org_id` | Active organization UUID |
| `roles` | `owner\|admin\|member\|viewer` |
| `exp` / `iat` | Expiry / issued |

**Access token TTL:** 15–60 minutes  
**Refresh token TTL:** 7–30 days (rotating)

```http
Authorization: Bearer eyJhbGciOiJSUzI1NiIsInR5cCI6IkpXVCJ9...
```

### 3.3 API Keys

- Prefix display: `spk_live_…` / `spk_test_…`
- Sent as `Authorization: Bearer spk_live_…` **or** `X-Api-Key: spk_live_…`
- Server stores **hash only**
- Scopes example: `audits:read`, `audits:write`, `reports:read`, `websites:write`

### 3.4 OAuth (Future)

Authorization Code + PKCE for dashboard; client credentials for M2M.

### 3.5 Roles & Permissions

| Role | Audits | Websites | Members | Billing | API Keys |
|---|---|---|---|---|---|
| owner | CRUD | CRUD | CRUD | CRUD | CRUD |
| admin | CRUD | CRUD | CRUD | read | CRUD |
| member | CRUD own/project | CRUD | read | — | — |
| viewer | read | read | read | — | — |
| anonymous | create+read by id | — | — | — | — |

> [!WARNING]
> Never accept roles from client body. Derive from token/membership.

---

## 4. API Resources

| Resource | Path prefix | Description |
|---|---|---|
| Users | `/users`, `/auth` | Identity |
| Organizations | `/organizations` | Tenants |
| Projects | `/organizations/{org_id}/projects` | Website groups |
| Websites | `/websites` or nested under projects | Managed sites |
| Audit Runs | `/audits` | Analysis instances |
| Engine Executions | `/audits/{id}/engines` | Per-engine runs |
| Engine Results | `/audits/{id}/engines/{engine}/result` | Typed outputs |
| Findings | `/audits/{id}/findings`, `/findings/{id}` | Issues |
| Recommendations | `/audits/{id}/recommendations`, `/recommendations/{id}` | Actions |
| AI Explanations | `/audits/{id}/ai/*`, `/findings/{id}/ai/*`, `/recommendations/{id}/ai/*` | Live OpenAI explanations (no persistence) |
| Reports | `/audits/{id}/report`, `/reports/{id}` | Assembled artifact |
| Monitoring Jobs | `/monitoring-jobs` | Schedules |
| Subscriptions | `/organizations/{org_id}/subscription` | Plans |
| API Keys | `/organizations/{org_id}/api-keys` | Programmatic auth |
| Health | `/health` | Liveness |

**ID types:** UUID strings unless noted. Public share links may use the same audit/report UUID.

---

## 5. Endpoint Specification Template

Every endpoint below follows:

| Field | Content |
|---|---|
| Purpose | Why it exists |
| Method / URL | HTTP + path |
| Headers | Required/optional |
| Auth | none / jwt / api_key |
| Permissions | Role/scope |
| Request | Schema + example |
| Response | Schema + example |
| Validation | Rules |
| Status codes | Success + errors |
| Rate limits | Class |
| Notes | Warnings |

---

## 6. Audit Endpoints

### 6.1 `POST /api/v1/audits`

| | |
|---|---|
| **Purpose** | Create a new Audit Run (orchestration entrypoint) |
| **Method** | `POST` |
| **URL** | `/api/v1/audits` |
| **Auth** | Optional (anonymous allowed) — auth/entitlements not yet enforced |
| **Permissions** | `audits:write` or anonymous quota (future) |
| **Idempotency** | Honor `Idempotency-Key` (future; not yet implemented) |

**Headers**

| Header | Required |
|---|---|
| `Content-Type: application/json` | Yes |
| `Idempotency-Key` | Recommended (future) |
| `Authorization` | If authenticated (future) |

#### Implemented request body (current)

```json
{
  "website_id": "w1111111-1111-1111-1111-111111111111"
}
```

| Field | Type | Rules |
|---|---|---|
| `website_id` | uuid | Required. Website must exist and not be soft-deleted (`WEBSITE_NOT_FOUND` otherwise) |

#### Implemented response `201 Created`

```json
{
  "audit_id": "a1b2c3d4-e5f6-7890-abcd-ef1234567890",
  "status": "pending",
  "message": "Audit created successfully."
}
```

| Field | Type | Notes |
|---|---|---|
| `audit_id` | uuid | New AuditRun id |
| `status` | string | Always `pending` on create |
| `message` | string | Human-readable confirmation |

**Status codes (current)**

| Code | When |
|---|---|
| 201 | AuditRun persisted successfully |
| 404 | Website missing or soft-deleted (`WEBSITE_NOT_FOUND`) |
| 422 | Validation error (invalid UUID / body) |

> [!IMPORTANT]
> **Architecture note:** The endpoint currently returns **HTTP 201** because the AuditRun resource is created **synchronously** in the API request (no worker enqueue yet). When asynchronous job processing (Celery, Dramatiq, Temporal, etc.) is introduced, the endpoint **may transition to HTTP 202 Accepted** while retaining the same pollable `audit_id` contract. Clients should treat `audit_id` + `GET /api/v1/audits/{audit_id}` as the durable progress path either way.

#### Target request body (future — not yet implemented)

retained for product/API roadmap; do not assume these fields work today:

```json
{
  "url": "https://example.com",
  "website_id": null,
  "project_id": null,
  "organization_id": null,
  "options": {
    "strategy": "mobile",
    "force_refresh": false
  }
}
```

| Field | Type | Rules |
|---|---|---|
| `url` | string | Required if `website_id` null; ≤ 2048; http(s) |
| `website_id` | uuid\|null | If set, URL optional (uses canonical) |
| `options.strategy` | enum | `mobile` \| `desktop` |
| `options.force_refresh` | bool | Bypass crawl cache |

Future response may also include `url`, `created_at`, `status_url`, and `report_url`. Future status codes remain relevant once engines and entitlements land: `400` (`INVALID_URL`, `SSRF_BLOCKED`), `401`, `403`, `409` (`ANALYSIS_IN_PROGRESS`), `429`.

**Rate limit class:** `audits_create` (e.g., 5 / 10 min / IP anonymous) — planned

> [!NOTE]
> PRD alias: `POST /api/v1/analyze` may redirect or duplicate this contract for backward compatibility during migration. Prefer `/audits`.

---

### 6.2 `GET /api/v1/audits`

| | |
|---|---|
| **Purpose** | List Audit Runs for the active org/project |
| **Auth** | JWT or API key **required** |
| **Permissions** | `audits:read` |

**Query**

| Param | Type | Description |
|---|---|---|
| `website_id` | uuid | Filter |
| `project_id` | uuid | Filter |
| `status` | string | Filter |
| `page_size` | int | 1–100, default 20 |
| `cursor` | string | Opaque |
| `sort` | string | default `created_at:desc` |

**Response `200`**

```json
{
  "data": [
    {
      "audit_id": "a1b2c3d4-e5f6-7890-abcd-ef1234567890",
      "website_id": "w111...",
      "url": "https://example.com/",
      "status": "complete",
      "health_score": 82,
      "created_at": "2026-07-12T10:15:00Z",
      "completed_at": "2026-07-12T10:15:42Z"
    }
  ],
  "next_cursor": null
}
```

---

### 6.3 `GET /api/v1/audits/{audit_id}`

| | |
|---|---|
| **Purpose** | Get Audit Run status + summary scores (frontend polling target) |
| **Auth** | Optional if resource is anonymously created and unlisted-token policy allows; else JWT/API key |
| **Permissions** | `audits:read` or knowledge of id |

**Response `200` (Sprint 14 — enriched summary; no recommendations / AI)**

```json
{
  "audit_id": "a1b2c3d4-e5f6-7890-abcd-ef1234567890",
  "website_id": "w1111111-1111-1111-1111-111111111111",
  "url": "https://example.com/",
  "canonical_url": "https://example.com/",
  "status": "complete",
  "progress": 100,
  "current_engine": null,
  "scores": {
    "overall": 88,
    "seo": 90,
    "performance": 92,
    "security": 80,
    "accessibility": 85,
    "business": 87,
    "roi": null
  },
  "health_score": {
    "overall_score": 88,
    "category_scores": {
      "seo": 90,
      "accessibility": 85,
      "security": 80,
      "performance": 92,
      "business": 87
    },
    "grade": "B+",
    "confidence": 95,
    "breakdown": {},
    "configuration_version": "scoring_config@sprint13"
  },
  "category_scores": {
    "seo": 90,
    "accessibility": 85,
    "security": 80,
    "performance": 92,
    "business": 87
  },
  "engine_summary": [
    {
      "engine_name": "url_validation",
      "status": "success",
      "duration_ms": 12,
      "started_at": "2026-07-12T10:15:01Z",
      "completed_at": "2026-07-12T10:15:01Z",
      "error_message": null
    }
  ],
  "finding_counts": {
    "total": 3,
    "critical": 0,
    "high": 1,
    "medium": 1,
    "low": 1,
    "info": 0,
    "by_engine": { "seo": 2, "accessibility": 1 }
  },
  "failure_code": null,
  "failure_message": null,
  "duration_ms": 4200,
  "started_at": "2026-07-12T10:15:01Z",
  "completed_at": "2026-07-12T10:15:05Z",
  "created_at": "2026-07-12T10:15:00Z",
  "updated_at": "2026-07-12T10:15:05Z"
}
```

| Field | Type | Notes |
|---|---|---|
| `progress` | int | Maps from DB `progress_percent`; range **0–100** (10% steps per engine in Sprint 14) |
| `current_engine` | string\|null | Maps from DB `current_engine`; null when terminal |
| `scores.*` | int\|null | Denormalized category scores on `audit_runs` |
| `health_score` | object\|null | From `health_scores` (overall, grade, confidence, breakdown, configuration_version) |
| `category_scores` | object\|null | Category ints (also nested under `health_score`) |
| `engine_summary` | array | From `engine_executions` |
| `finding_counts` | object | Aggregates from `audit_findings` (no finding bodies on this endpoint) |
| `duration_ms` | int\|null | Audit wall time |

**Progress tracking**

| Concept | Field | Range / rules | Purpose |
|---|---|---|---|
| Progress | `progress` (`progress_percent`) | 0–100 | Live audit progress for frontend polling |
| Current engine | `current_engine` | nullable string | Frontend progress label; future worker / orchestrator coordination |

Polling flow (product): Landing → `POST /api/v1/audits` (runs pipeline synchronously today) → navigate `/audit/{audit_id}` → poll this endpoint until a terminal status.

> **Sprint 14/15:** `POST /api/v1/audits` creates the AuditRun **and** executes `AuditPipeline` in-process through Health + Recommendation. Response status is typically `complete` / `complete_with_warnings` / `failed` (not `pending`). Async `202` enqueue remains a future option. GET includes rule-based `recommendations` (priority summary, quick wins, counts) — **not** AI prose, ROI, or executive narratives.

#### Audit Status values

| Status | Meaning |
|---|---|
| `pending` | AuditRun created; pipeline not started |
| `validating` | URL Validation in progress |
| `crawling` | Crawl in progress |
| `parsing` | HTML parser in progress (Sprint 14 fine-grained) |
| `seo` | SEO engine in progress |
| `accessibility` | Accessibility engine in progress |
| `security` | Security engine in progress |
| `performance` | Performance engine in progress |
| `business` | Business intelligence engine in progress |
| `health` | Health score engine in progress |
| `recommendation` | Recommendation & Priority engine in progress |
| `analyzing` | Coarse: analysis engines running (legacy / aggregate) |
| `scoring` | Coarse: Health / category scoring in progress |
| `enriching` | Business Impact, ROI, DQ, and/or AI enrichment |
| `building_report` | Report assembly in progress |
| `complete` | Terminal success |
| `complete_with_warnings` | Terminal success with soft gaps (e.g. partial engine status) |
| `failed` | Terminal failure |
| `cancelled` | Terminal cancellation |

Do **not** use obsolete values such as `processing`, `queued`, or `running` in API responses.

**Status codes:** `200`, `404` (`AUDIT_NOT_FOUND`)

**Alias (future):** `GET /api/v1/audits/{audit_id}/status` may return a reduced projection (`audit_id`, `status`, `progress`, `current_engine`).

---

### 6.4 `DELETE /api/v1/audits/{audit_id}`

| | |
|---|---|
| **Purpose** | Soft-delete an Audit Run (and hide from lists) |
| **Auth** | JWT/API key required |
| **Permissions** | `audits:write` + ownership |

**Response `204 No Content`**

Errors: `404 AUDIT_NOT_FOUND`, `403 FORBIDDEN`

---

### 6.5 `POST /api/v1/audits/{audit_id}/cancel`

| | |
|---|---|
| **Purpose** | Cancel in-flight pipeline |
| **Auth** | JWT/API key or anonymous creator policy |
| **Response** | `200` with updated status `cancelled` or `409` if already terminal |

---

## 7. Report Endpoints

### 7.1 `GET /api/v1/audits/{audit_id}/report`

| | |
|---|---|
| **Purpose** | Fetch assembled Report JSON (dashboard source of truth) |
| **Auth** | Same visibility rules as audit |
| **Permissions** | `reports:read` |

**Response `200`** (truncated)

```json
{
  "report_id": "r999...",
  "audit_id": "a1b2c3d4-e5f6-7890-abcd-ef1234567890",
  "url": "https://example.com/",
  "status": "ready",
  "schema_version": "report.v1",
  "overview": {
    "title": "Example Domain",
    "meta_description": null,
    "status_code": 200,
    "https": true,
    "favicon": "https://example.com/favicon.ico"
  },
  "scores": {
    "overall": 82,
    "seo": 82,
    "performance": 68,
    "security": 94,
    "accessibility": 86,
    "best_practices": 98
  },
  "executive_summary": "example.com scores 82/100 overall...",
  "business_summary": {
    "quick_wins": [],
    "strategic_fixes": []
  },
  "issues": [
    {
      "id": "iss_001",
      "finding_id": "seo.meta_description.missing",
      "category": "seo",
      "issue": "Missing Meta Description",
      "business_impact": "Lower CTR from Search",
      "expected_outcome": "Improved snippet quality in search results",
      "difficulty": "Easy",
      "estimated_time": "5 minutes",
      "priority": "High",
      "confidence": 100,
      "technical_explanation": "No <meta name='description'> tag found in <head>.",
      "recommended_action": "Add a unique 50-160 character meta description.",
      "business_explanation": "Search engines are writing their own snippet..."
    }
  ],
  "charts": {
    "priority_breakdown": { "Critical": 1, "High": 3, "Medium": 5, "Low": 2 }
  },
  "estimated_total_effort": "14-22 hours",
  "pdf_url": null,
  "created_at": "2026-07-12T10:15:42Z",
  "completed_at": "2026-07-12T10:15:42Z"
}
```

**Status codes:** `200`, `404 AUDIT_NOT_FOUND` (or `REPORT_NOT_FOUND` when resolving by report id), `409 REPORT_NOT_READY` (audit not complete)

> **Sprint 16:** Implemented as `ReportComposer` (`app/services/report/`) returning `AuditReportDTO` with sectioned overview/health/categories/recommendations/statistics/engine_summary. Projection cached in `reports.report_json`. Regeneration: `POST /api/v1/audits/{audit_id}/report/regenerate`.

**PRD alias:** `GET /api/v1/report/{id}` where `{id}` is `audit_id` or `report_id` (document resolution order: try audit_id first).

---

### 7.2 Report export (Sprint 30)

Presentation-only downloads of the **already assembled** `AuditReportDTO`. No AI, no engines, no pipeline, no Report Composer changes — exporters call `GetAuditReportUseCase` then render.

| Method | Path | Content-Type | Filename |
|---|---|---|---|
| `GET` | `/api/v1/audits/{audit_id}/export/pdf` | `application/pdf` | `audit-report.pdf` |
| `GET` | `/api/v1/audits/{audit_id}/export/json` | `application/json` | `audit-report.json` |
| `GET` | `/api/v1/audits/{audit_id}/export/csv` | `text/csv; charset=utf-8` | `audit-report.csv` |

**Response headers (all formats):**

```http
Content-Disposition: attachment; filename="audit-report.pdf"
```

| Code | Body code | When |
|---|---|---|
| 200 | — | File bytes |
| 404 | `AUDIT_NOT_FOUND` | Audit missing |
| 409 | `REPORT_NOT_READY` | Audit not complete |
| 503 | `EXPORT_FAILED` | Renderer failure |

**JSON:** exact `AuditReportDTO` (`model_dump_json`), no extra fields.  
**CSV:** Findings (`Category,Severity,Title,Description,Impact,Score`) + Recommendations (`Priority,Recommendation,Difficulty,Expected Impact,Quick Win`), UTF-8 with BOM.  
**PDF:** cover, scores, executive/business summaries, findings, recommendations, quick wins, footer + page numbers (ReportLab).

> Legacy URL-style `GET …/report/pdf` (signed `pdf_url`) remains a future storage path; Sprint 30 ships **attachment downloads** under `/export/*`.

---

### 7.3 `POST /api/v1/audits/{audit_id}/report/regenerate`


| | |
|---|---|
| **Purpose** | Rebuild Report from persisted engine artifacts (no full recrawl) |
| **Auth** | JWT/API key |
| **Permissions** | `reports:write` |
| **Response** | `202` with new report version |

---

### 7.4 Report sharing (Sprint 31)

Read-only presentation links. Tokens are **HMAC-signed** (`SECRET_KEY`), URL-safe, and **not stored in the database**. Recipients receive the same `AuditReportDTO` via `GetAuditReportUseCase` — Report Composer is never duplicated.

#### `POST /api/v1/audits/{audit_id}/share`

| | |
|---|---|
| **Purpose** | Mint a time-limited share URL for a completed report |
| **Auth (MVP)** | none (same as report reads) |
| **Response** | `201` |

```json
{
  "share_url": "http://localhost:3000/share/{token}",
  "token": "{token}",
  "expires_at": "2026-07-20T00:00:00Z",
  "audit_id": "a1b2c3d4-e5f6-7890-abcd-ef1234567890"
}
```

| Status | Code | When |
|---|---|---|
| 404 | `AUDIT_NOT_FOUND` | Unknown audit |
| 409 | `REPORT_NOT_READY` | Audit incomplete |

Config: `PUBLIC_WEB_URL`, `SHARE_TOKEN_TTL_SECONDS` (default 7 days), `SECRET_KEY`.

#### `GET /api/v1/share/{token}`

| | |
|---|---|
| **Purpose** | Fetch `AuditReportDTO` for a shared link (read-only) |
| **Auth (MVP)** | none |
| **Response** | `200` — same DTO as `GET …/report` |

| Status | Code | When |
|---|---|---|
| 404 | `SHARE_TOKEN_INVALID` | Missing, malformed, or tampered token |
| 410 | `SHARE_TOKEN_EXPIRED` | Past `exp` |

Frontend: `/share/[token]` → `ReportDashboard` with `readonly=true` (hides AI generate/regenerate, export, and share).

---

## 7A. AI Explanation Endpoints (Sprint 23 / 23.1)

Live OpenAI explanations of **completed** audit artifacts. The API is orchestration only:

```
HTTP → Application Use Case → AIService → Mapper → Builder → Session → Provider → Grounding → AIResponse[T]
```

Nothing is required of clients for persistence (Sprint 24). Generations are stored best-effort in `ai_generations` after grounding; HTTP JSON and headers remain unchanged. Duplicate identical content reuses the same immutable `version`.

Routers are feature-split under `app/api/v1/ai/` (`findings.py`, `recommendations.py`, `reports.py`) and tagged **`AI`** in OpenAPI. Use cases live under `app/application/ai/{findings,recommendations,reports}/`.

```mermaid
sequenceDiagram
    participant Client
    participant API as FastAPI router
    participant UC as Application use case
    participant Report as GetAuditReportUseCase
    participant Map as AI Context Mapper
    participant AI as AIService
    participant GW as GroundingValidator

    Client->>API: GET .../ai/...
    API->>UC: execute(id)
    UC->>Report: load AuditReportDTO
    Report-->>UC: report / 404 / 409
    UC->>Map: DTO → AIContext
    UC->>AI: explain_* / generate_*
    AI->>GW: validate closed-world
    GW-->>AI: ok | InvalidAIResponse
    AI-->>UC: AIResponse[T]
    UC-->>API: AIResponse[T]
    API-->>Client: 200 AIResponse JSON + X-AI-* headers
```

### 7A.1 Endpoints

| Method | URL | operationId | Use case |
|---|---|---|---|
| GET | `/api/v1/audits/{audit_id}/ai/executive-summary` | `getAuditAiExecutiveSummary` | `GenerateExecutiveSummaryUseCase` |
| GET | `/api/v1/audits/{audit_id}/ai/business-summary` | `getAuditAiBusinessSummary` | `GenerateBusinessSummaryUseCase` |
| GET | `/api/v1/findings/{finding_id}/ai/explanation` | `getFindingAiExplanation` | `GenerateFindingExplanationUseCase` |
| GET | `/api/v1/recommendations/{recommendation_id}/ai/explanation` | `getRecommendationAiExplanation` | `GenerateRecommendationExplanationUseCase` |
| GET | `/api/v1/recommendations/{recommendation_id}/ai/quick-win` | `getRecommendationAiQuickWin` | `GenerateQuickWinExplanationUseCase` |

### 7A.1.1 Regeneration & history (Sprint 25)

Controlled regeneration creates a **new immutable** `ai_generations` version when content changes. Identical `response_hash` reuses the existing version. Latest is always `max(version)` for the current report hash — no mutable pointer column.

| Method | URL | Notes |
|---|---|---|
| POST | `/api/v1/findings/{id}/ai/regenerate` | New version or reuse |
| POST | `/api/v1/recommendations/{id}/ai/regenerate` | Recommendation explanation |
| POST | `/api/v1/recommendations/{id}/ai/regenerate-quick-win` | Quick win |
| POST | `/api/v1/audits/{id}/ai/regenerate-executive-summary` | Executive summary |
| POST | `/api/v1/audits/{id}/ai/regenerate-business-summary` | Business summary |
| GET | `…/ai/latest` (or `…/ai/{feature}/latest`) | Highest version for current report |
| GET | `…/ai/versions` | `GenerationHistoryDTO` (metadata only) |
| GET | `…/ai/versions/{version}` | Stored `AIResponse` for that version |

Quick-win history paths nest under `/ai/quick-win/…`. Audit summary history nests under `/ai/executive-summary/…` and `/ai/business-summary/…`.

**History item fields:** `version`, `created_at`, `provider`, `model`, `prompt_version`, `schema_version`, `generation_id`, `response_hash` — no narrative duplication.

**Errors:** `404 GENERATION_NOT_FOUND` when latest/version is missing.

**Auth (MVP):** none (same as audit/report reads today).

**OpenAPI:** tag `AI`; each operation includes summary, description, response examples, and error docs.

**Path ID notes:**
- `{finding_id}` = `audit_findings.id` (row UUID), not the business rule key
- `{recommendation_id}` = `recommendations.id` (row UUID), not the business key
- Quick win returns `409 AI_FEATURE_UNAVAILABLE` when `is_quick_win` is false

### 7A.1.2 Async generation jobs (Sprint 26)

Clients may enqueue generation instead of waiting on the request path:

```
POST …/ai/generate*  →  202 { job_id, status: "queued" }
GET  /api/v1/jobs/{job_id}  →  status (+ generation_id when completed)
GET  /api/v1/jobs/{job_id}/result  →  stored AIResponse (409 if not completed)
POST /api/v1/jobs/{job_id}/cancel  →  cancel queued job
GET  /api/v1/jobs  →  list (optional feature / entity_id / audit_id / status filters)
```

| Method | URL | Notes |
|---|---|---|
| POST | `/api/v1/findings/{id}/ai/generate` | Finding explanation job |
| POST | `/api/v1/recommendations/{id}/ai/generate` | Recommendation explanation job |
| POST | `/api/v1/recommendations/{id}/ai/generate-quick-win` | Quick win job |
| POST | `/api/v1/audits/{id}/ai/generate-executive-summary` | Executive summary job |
| POST | `/api/v1/audits/{id}/ai/generate-business-summary` | Business summary job |
| GET | `/api/v1/jobs/{job_id}` | Poll status |
| GET | `/api/v1/jobs/{job_id}/result` | Completed `AIResponse` |
| POST | `/api/v1/jobs/{job_id}/cancel` | Cancel if still queued |
| GET | `/api/v1/jobs` | List jobs |

**Queue:** `QueuePort` with selectable backend (`AI_QUEUE_BACKEND=inmemory|redis`). Default `inmemory` runs `BackgroundWorker` via FastAPI `BackgroundTasks` after `202`. Redis mode enqueues only; run `python -m app.ai.jobs.worker_main`. The HTTP path **commits the job row before enqueue** so workers never observe an uncommitted id. Visibility timeout + distributed lock prevent lost/duplicate work. Job poll/result JSON contracts are unchanged.

**Job errors:** `404 JOB_NOT_FOUND`, `409 JOB_NOT_COMPLETE`, `400 JOB_ALREADY_RUNNING`, `400 JOB_ALREADY_COMPLETED`.

**Sprint 26.1 job poll fields (additive):** `progress` (0–100), `queued_at`, `queue_wait_ms`, `execution_ms`, `total_duration_ms`, `worker` (`local-worker-1`), `max_attempts`, `next_retry_at`, `last_error`, `cancel_reason`. When `completed`: also `generation_id`, `latest_version`, `result_url` (e.g. `/api/v1/jobs/{id}/result` — clients must not construct URLs).

**Sprint 26.2 diagnostics (additive):** `summary`, `events`, `phase_history`, `failure_category`, `health` (`is_running` / `is_terminal` / `is_success` / `is_failure`), plus mirrored provider fields `provider`, `model`, `latency_ms`, `cached`, `finish_reason`, `retry_count` (derived from stored AIResponse metadata — not duplicated as job columns).

**Sprint 26.3 lifecycle (additive):** `expires_at`, `expired`, `cleanup_candidate`, `stale`, `age_ms`, `duration_class` (`FAST`…`VERY_SLOW`), `queue_class` (`IMMEDIATE`…`LONG`). Nothing deletes job rows.

Sync `GET …/explanation` endpoints remain available. Regeneration (Sprint 25) is unchanged.

### 7A.2 Response shape

Returns the complete `AIResponse[T]` envelope (not flattened). JSON body is unchanged from Sprint 23.

```json
{
  "generation_id": "6f2c8a1e-…",
  "result": { "...": "feature-specific schema" },
  "quality": {
    "grounded": true,
    "validation_passed": true,
    "cache_hit": false,
    "provider": "openai",
    "model": "gpt-5.5",
    "prompt_version": "v1",
    "builder_version": 1,
    "schema_version": "ai.executive_summary.v3",
    "feature": "executive_summary"
  },
  "provider_metadata": {
    "provider": "openai",
    "model": "gpt-5.5",
    "latency_ms": 420,
    "tokens_in": 800,
    "tokens_out": 200,
    "cached": false,
    "retry_count": 0
  },
  "telemetry": { "...": "GenerationTelemetry" },
  "diagnostics": null,
  "session_id": "…",
  "generated_at": "2026-07-12T02:30:00Z"
}
```

### 7A.2.1 Observability headers (Sprint 23.1)

Successful `200` responses also expose existing `AIResponse` fields as headers (copied, never recomputed):

| Header | Source |
|---|---|
| `X-Generation-ID` | `AIResponse.generation_id` |
| `X-AI-Provider` | `provider_metadata.provider` |
| `X-AI-Model` | `provider_metadata.model` |
| `X-AI-Cached` | `provider_metadata.cached` → `true` / `false` |
| `X-AI-Feature` | `quality.feature` (fallback: `provider_metadata.feature`) |

### 7A.3 Status codes

| HTTP | Code | When |
|---|---|---|
| 200 | — | Grounded explanation / job status / history |
| 202 | — | Async generation job accepted (`job_id`) |
| 400 | `JOB_ALREADY_RUNNING` | Cancel rejected — job running |
| 400 | `JOB_ALREADY_COMPLETED` | Cancel rejected — job completed |
| 404 | `AUDIT_NOT_FOUND` | Unknown audit |
| 404 | `FINDING_NOT_FOUND` | Unknown finding row UUID |
| 404 | `RECOMMENDATION_NOT_FOUND` | Unknown recommendation row UUID |
| 404 | `GENERATION_NOT_FOUND` | No persisted AI generation / version |
| 404 | `JOB_NOT_FOUND` | Unknown AI generation job |
| 409 | `REPORT_NOT_READY` | Audit not complete |
| 409 | `AI_FEATURE_UNAVAILABLE` | e.g. quick-win on non–quick-win recommendation |
| 409 | `JOB_NOT_COMPLETE` | Result requested before job completed |
| 422 | `INVALID_AI_RESPONSE` | Schema parse or grounding failure |
| 503 | `UPSTREAM_UNAVAILABLE` | Provider timeout / API error |
| 503 | `NOT_READY` | Missing configuration / service not ready |

---

## 8. Engine Endpoints

Engine resources are **read models** of pipeline artifacts. Clients do not invoke engines directly in MVP (orchestrator owns execution). Optional admin/debug triggers may exist behind internal auth.

### 8.1 List engines for an audit

`GET /api/v1/audits/{audit_id}/engines`

**Response `200`**

```json
{
  "data": [
    {
      "engine_name": "seo_intelligence",
      "engine_version": "1.4.0",
      "status": "success",
      "attempt": 1,
      "execution_time_ms": 842,
      "started_at": "2026-07-12T10:15:05Z",
      "completed_at": "2026-07-12T10:15:06Z"
    }
  ]
}
```

---

### 8.2 Get engine execution + result

`GET /api/v1/audits/{audit_id}/engines/{engine_name}`

`engine_name` enum:  
`url_validation`, `crawler`, `html_parser`, `seo_intelligence`, `performance`, `security`, `accessibility`, `health_score`, `business_impact`, `roi`, `data_quality`, `ai_recommendation`, `report_builder`, `pdf`

**Response `200`**

```json
{
  "engine_name": "performance",
  "status": "success",
  "engine_version": "1.2.0",
  "execution_time_ms": 18200,
  "result": {
    "schema_version": "engine.performance.output.v1",
    "structured_output": {
      "data": {
        "metrics": { "lcp_ms": 4300, "performance_score": 48 },
        "findings": []
      }
    },
    "confidence": 98
  }
}
```

> [!WARNING]
> `raw_output` (PSI/LLM) is **not** returned by default. Use `?include_raw=true` with admin scope only.

---

### 8.3 Category convenience endpoints

These are projections over Findings / engine results for UI tabs.

| Method | URL | Purpose |
|---|---|---|
| GET | `/api/v1/audits/{audit_id}/engines/health_score` | Health Score Engine output |
| GET | `/api/v1/audits/{audit_id}/categories/seo` | SEO findings + metrics |
| GET | `/api/v1/audits/{audit_id}/categories/performance` | Performance |
| GET | `/api/v1/audits/{audit_id}/categories/security` | Security |
| GET | `/api/v1/audits/{audit_id}/categories/accessibility` | Accessibility |
| GET | `/api/v1/audits/{audit_id}/categories/business-impact` | Business impact enriched issues |
| GET | `/api/v1/audits/{audit_id}/categories/roi` | ROI enriched issues |
| GET | `/api/v1/audits/{audit_id}/recommendations` | See §9 |

**Example — SEO category `200`**

```json
{
  "category": "seo",
  "score": 82,
  "metrics": { "title_length": 14, "meta_description_length": 0 },
  "findings": []
}
```

---

### 8.4 Internal re-run (non-public MVP)

`POST /api/v1/internal/audits/{audit_id}/engines/{engine_name}/rerun`

- Auth: service JWT / admin only  
- Purpose: recompute one engine from stored artifacts  
- Response: `202`

---

## 9. Finding & Recommendation Endpoints

### 9.1 `GET /api/v1/audits/{audit_id}/findings`

**Query:** `priority`, `category`, `severity`, `resolution_status`, `min_confidence`, `page_size`, `cursor`

**Response `200`**

```json
{
  "data": [
    {
      "id": "f111...",
      "finding_id": "seo.meta_description.missing",
      "category": "seo",
      "severity": "high",
      "priority": "High",
      "confidence": 100,
      "issue": "Missing Meta Description",
      "business_impact": "Lower CTR from Search",
      "recommended_action": "Add a unique 50-160 character meta description.",
      "resolution_status": "open"
    }
  ],
  "next_cursor": null
}
```

### 9.2 `PATCH /api/v1/audits/{audit_id}/findings/{finding_id}`

Update `resolution_status` (`open|accepted|resolved|wontfix|reopened`). Auth required.

### 9.3 `GET /api/v1/audits/{audit_id}/recommendations`

Returns AI/fallback recommendations with `prompt_version`, `model_used`, `confidence`, `is_fallback`.

### 9.4 `POST /api/v1/audits/{audit_id}/recommendations/regenerate`

Re-run AI Recommendation Engine after DQ (no crawl). `202`. Requires `audits:write`.

---

## 10. Monitoring Endpoints

Future scheduled monitoring (V2+).

### 10.1 `POST /api/v1/monitoring-jobs`

```json
{
  "website_id": "w111...",
  "frequency": "weekly",
  "cron": null,
  "timezone": "UTC"
}
```

**Response `201`**

### 10.2 `GET /api/v1/monitoring-jobs`

List jobs for org. Auth required. Entitlement: Agency+.

### 10.3 `GET /api/v1/monitoring-jobs/{job_id}`

### 10.4 `PATCH /api/v1/monitoring-jobs/{job_id}`

Pause/resume/update schedule.

### 10.5 `DELETE /api/v1/monitoring-jobs/{job_id}`

Soft-delete / retire.

---

## 11. User Endpoints

### 11.1 `POST /api/v1/auth/register`

```json
{
  "email": "founder@example.com",
  "password": "correct-horse-battery-staple",
  "full_name": "Ada Lovelace"
}
```

**Response `201`** — user + org bootstrap (personal workspace)

Validation: email format; password ≥ 12 chars; breach check recommended.

### 11.2 `POST /api/v1/auth/login`

```json
{ "email": "founder@example.com", "password": "..." }
```

**Response `200`**

```json
{
  "access_token": "<jwt>",
  "refresh_token": "<opaque>",
  "token_type": "bearer",
  "expires_in": 1800,
  "user": { "id": "u1...", "email": "founder@example.com" }
}
```

### 11.3 `POST /api/v1/auth/refresh`

```json
{ "refresh_token": "..." }
```

### 11.4 `POST /api/v1/auth/logout`

Invalidate refresh token / session.

### 11.5 `GET /api/v1/users/me`

Profile for current user.

### 11.6 `PATCH /api/v1/users/me`

Update `full_name`, `avatar_url`, settings.

### 11.7 `GET /api/v1/users/me/settings` / `PUT /api/v1/users/me/settings`

Notification and UI preferences.

---

## 12. Organization, Project & Website Endpoints

### 12.1 Organizations

| Method | URL | Purpose |
|---|---|---|
| GET | `/organizations` | List memberships |
| POST | `/organizations` | Create org |
| GET | `/organizations/{org_id}` | Get org |
| PATCH | `/organizations/{org_id}` | Update name/settings |
| GET | `/organizations/{org_id}/members` | List members |
| POST | `/organizations/{org_id}/members` | Invite member |
| PATCH | `/organizations/{org_id}/members/{user_id}` | Change role |
| DELETE | `/organizations/{org_id}/members/{user_id}` | Remove member |

**Invite body**

```json
{ "email": "dev@agency.com", "role": "member" }
```

### 12.2 Projects

| Method | URL | Purpose |
|---|---|---|
| GET | `/organizations/{org_id}/projects` | List |
| POST | `/organizations/{org_id}/projects` | Create |
| GET | `/projects/{project_id}` | Get |
| PATCH | `/projects/{project_id}` | Update |
| DELETE | `/projects/{project_id}` | Soft-delete |

**Create body**

```json
{ "name": "Client Contoso", "slug": "client-contoso", "description": null }
```

### 12.3 Websites

| Method | URL | Purpose |
|---|---|---|
| POST | `/websites` | Bootstrap website from URL (Sprint 28) |
| GET | `/projects/{project_id}/websites` | List (future) |
| POST | `/projects/{project_id}/websites` | Register website under project (future) |
| GET | `/websites/{website_id}` | Get |
| PATCH | `/websites/{website_id}` | Update metadata |
| DELETE | `/websites/{website_id}` | Soft-delete |
| GET | `/websites/{website_id}/audits` | Audits for site |

**Sprint 28 bootstrap** — `POST /api/v1/websites`

```json
{ "url": "https://example.com" }
```

Auto-provisions a default local org/project when none exist (unauthenticated MVP). Idempotent per canonical URL within that project. Response: `WebsiteResponse` (`id`, `canonical_url`, `host`, …). Frontend then calls `POST /audits` with `website_id`.

**Nested create body (future)**

```json
{
  "url": "https://contoso.com",
  "industry": "saas",
  "country": null
}
```

---

## 13. Subscription & API Key Endpoints

### 13.1 Subscription

| Method | URL | Purpose |
|---|---|---|
| GET | `/organizations/{org_id}/subscription` | Current plan |
| POST | `/organizations/{org_id}/subscription/checkout` | Billing session (future) |
| POST | `/organizations/{org_id}/subscription/portal` | Customer portal (future) |

**Plans:** `free`, `pro`, `business`, `agency`, `enterprise`

### 13.2 API Keys

| Method | URL | Purpose |
|---|---|---|
| GET | `/organizations/{org_id}/api-keys` | List (prefixes only) |
| POST | `/organizations/{org_id}/api-keys` | Create (returns secret once) |
| DELETE | `/organizations/{org_id}/api-keys/{key_id}` | Revoke |

**Create response `201`**

```json
{
  "id": "k1...",
  "name": "CI",
  "key_prefix": "spk_live_ab12",
  "api_key": "spk_live_ab12...FULL_SECRET_ONCE",
  "permissions": ["audits:read", "audits:write", "reports:read"],
  "expires_at": null
}
```

> [!WARNING]
> The full `api_key` is returned **once**. It cannot be retrieved again.

---

## 14. System Endpoints

### 14.1 `GET /api/v1/health`

```json
{
  "status": "ok",
  "version": "1.0.0",
  "uptime_seconds": 183921
}
```

### 14.2 `GET /api/v1/ready`

Checks Postgres + Redis. `200` or `503`.

### 14.3 Compatibility aliases (PRD)

| Alias | Canonical |
|---|---|
| `POST /api/v1/analyze` | `POST /api/v1/audits` |
| `GET /api/v1/report/{id}` | `GET /api/v1/audits/{id}/report` |
| `GET /api/v1/report/{id}/status` | `GET /api/v1/audits/{id}` (status projection) |
| `GET /api/v1/report/{id}/pdf` | `GET /api/v1/audits/{id}/report/pdf` |

---

## 15. Error Model

### 15.1 Envelope

All non-2xx responses:

```json
{
  "error": {
    "code": "INVALID_URL",
    "message": "The provided URL is not reachable or is not a valid public website.",
    "details": {
      "field": "url"
    },
    "request_id": "req_01H...",
    "retry_after": null
  }
}
```

### 15.2 Error code table

| HTTP | Code | Meaning |
|---|---|---|
| 400 | `INVALID_URL` | URL invalid / unreachable |
| 400 | `SSRF_BLOCKED` | Private/metadata target |
| 400 | `INVALID_SCHEME` | Non-http(s) |
| 401 | `UNAUTHORIZED` | Missing/invalid credentials |
| 403 | `FORBIDDEN` | Lacks permission/entitlement |
| 404 | `AUDIT_NOT_FOUND` | Unknown audit |
| 404 | `REPORT_NOT_FOUND` | Unknown report |
| 404 | `WEBSITE_NOT_FOUND` | Unknown website |
| 404 | `FINDING_NOT_FOUND` | Unknown finding row |
| 404 | `RECOMMENDATION_NOT_FOUND` | Unknown recommendation row |
| 409 | `ANALYSIS_IN_PROGRESS` | Duplicate in-flight |
| 409 | `REPORT_NOT_READY` | Audit incomplete |
| 409 | `AI_FEATURE_UNAVAILABLE` | AI feature not applicable to entity |
| 409 | `CONFLICT` | State conflict |
| 422 | `VALIDATION_ERROR` | Schema/field errors |
| 422 | `INVALID_AI_RESPONSE` | AI grounding / schema validation failed |
| 429 | `RATE_LIMITED` | Too many requests |
| 500 | `INTERNAL_ERROR` | Unhandled |
| 503 | `UPSTREAM_UNAVAILABLE` | PSI/LLM/PDF down |
| 503 | `NOT_READY` | Dependency not ready |

### 15.3 Validation error details

```json
{
  "error": {
    "code": "VALIDATION_ERROR",
    "message": "Request validation failed",
    "details": {
      "errors": [
        { "loc": ["body", "url"], "msg": "Field required", "type": "missing" }
      ]
    }
  }
}
```

---

## 16. Validation Rules

### 16.1 Request validation

| Rule | Enforcement |
|---|---|
| JSON schema via Pydantic | `extra=forbid` on public bodies |
| URL length ≤ 2048 | audits create |
| UUID path params | 422 if malformed |
| Enumerations | Closed sets |
| Password policy | register/login |
| Pagination bounds | `page_size` 1–100 |

### 16.2 Response validation

- CI contract tests validate response models against OpenAPI
- Scores 0–100 when present
- Confidence 0–100 on issues
- No stack traces in bodies

### 16.3 SSRF validation

Performed in URL Validation Engine before enqueue; API maps failures to `400 SSRF_BLOCKED` / `INVALID_URL`.

---

## 17. OpenAPI Spec

### 17.1 Info fragment (OpenAPI 3.1)

```yaml
openapi: 3.1.0
info:
  title: SitePilot AI API
  version: 1.0.0
  description: Your AI-powered Website Intelligence Platform.
servers:
  - url: https://api.sitepilot.ai/api/v1
  - url: http://localhost:8000/api/v1
tags:
  - name: Audits
  - name: Reports
  - name: Engines
  - name: Findings
  - name: Auth
  - name: Organizations
  - name: Websites
  - name: Monitoring
  - name: System
```

### 17.2 Security schemes

```yaml
components:
  securitySchemes:
    bearerAuth:
      type: http
      scheme: bearer
      bearerFormat: JWT
    apiKeyAuth:
      type: apiKey
      in: header
      name: X-Api-Key
```

### 17.3 Example path — create audit

```yaml
paths:
  /audits:
    post:
      tags: [Audits]
      summary: Create an audit run
      operationId: createAudit
      requestBody:
        required: true
        content:
          application/json:
            schema:
              type: object
              required: [website_id]
              properties:
                website_id: { type: string, format: uuid }
            example:
              website_id: w1111111-1111-1111-1111-111111111111
      responses:
        '201':
          description: AuditRun created
          content:
            application/json:
              schema:
                type: object
                required: [audit_id, status, message]
                properties:
                  audit_id: { type: string, format: uuid }
                  status: { type: string, example: pending }
                  message: { type: string }
        '404':
          description: Website not found (WEBSITE_NOT_FOUND)
          $ref: '#/components/responses/Error'
        '422':
          $ref: '#/components/responses/Error'
```

> Future OpenAPI may restore `202`, `Idempotency-Key`, and URL-based create once async workers and intake URL flow are implemented.
### 17.4 FastAPI generation

- Implement routers with Pydantic models
- Export OpenAPI at `/openapi.json`
- Publish artifact to `packages/types` / SDK generation
- Redoc/Swagger at `/docs` (non-prod or authenticated)

---

## 18. API Sequence Diagrams

### 18.1 Audit Flow

```mermaid
sequenceDiagram
    participant FE as Frontend
    participant API as FastAPI
    participant Q as Queue
    participant W as Worker
    participant DB as Postgres

    FE->>API: POST /audits {website_id}
    API->>DB: Insert AuditRun pending
    API-->>FE: 201 {audit_id, status, message}
    Note over API,Q: Future: enqueue pipeline → may return 202
    loop Poll until terminal status
      FE->>API: GET /audits/{id}
      API->>DB: Load status, progress_percent, current_engine, scores
      API-->>FE: status / progress / current_engine
    end
    Q->>W: Job (future)
    W->>DB: Engine results + findings + report (future)
    FE->>API: GET /audits/{id}/report (future)
    API-->>FE: report JSON
```

### 18.2 Report Generation / PDF

```mermaid
sequenceDiagram
    participant FE as Frontend
    participant API as FastAPI
    participant W as Worker
    participant S3 as Object Storage

    FE->>API: GET /audits/{id}/report/pdf
    alt PDF exists
      API-->>FE: 200 pdf_url
    else needs render
      API->>W: Enqueue PDF
      API-->>FE: 202 generating
      W->>S3: Upload PDF
      W->>API: Persist url
      FE->>API: GET pdf (retry)
      API-->>FE: 200 pdf_url
    end
```

### 18.3 Authentication

```mermaid
sequenceDiagram
    participant U as User
    participant API as FastAPI
    participant DB as Postgres

    U->>API: POST /auth/login
    API->>DB: Verify password hash
    API-->>U: access_token + refresh_token
    U->>API: GET /users/me (Authorization Bearer)
    API-->>U: profile
    U->>API: POST /auth/refresh
    API-->>U: new access_token
```

### 18.4 Monitoring (Future)

```mermaid
sequenceDiagram
    participant Sch as Scheduler
    participant API as API/Worker
    participant DB as Postgres

    Sch->>DB: Due monitoring jobs
    Sch->>API: Create audit for website_id
    API->>DB: Audit pending + link job
    Note over API: Standard audit pipeline
```

---

## 19. API Versioning Strategy

| Change type | Policy |
|---|---|
| Add optional field | Compatible — stay `v1` |
| Add endpoint | Compatible |
| Make field required | Breaking — `v2` or long deprecation |
| Rename/remove field | Breaking |
| Change error codes meaning | Breaking if clients depend |

**Deprecation headers (future):** `Deprecation`, `Sunset`  
**Compatibility aliases** remain at least one minor release after announcement.

---

## 20. Webhooks

Future outbound events for agencies/integrations.

### 20.1 Event types

| Event | Payload summary |
|---|---|
| `audit.completed` | audit_id, scores |
| `audit.failed` | audit_id, code |
| `report.ready` | report_id, audit_id |
| `monitoring.run` | job_id, audit_id |

### 20.2 Delivery

- HTTPS POST with signature header `X-SitePilot-Signature` (HMAC SHA-256)
- At-least-once; require idempotent receivers
- Retry with exponential backoff

### 20.3 Management endpoints (future)

`POST /organizations/{org_id}/webhooks`  
`GET /organizations/{org_id}/webhooks`  
`DELETE /organizations/{org_id}/webhooks/{webhook_id}`

---

## 21. Rate Limiting

| Dimension | Example MVP limits |
|---|---|
| **Per IP (anonymous)** | 5 `POST /audits` / 10 minutes |
| **Per user** | Plan-based monthly analysis quota + burst |
| **Per API key** | Higher sustained RPS; still fair-use |
| **Global PSI/LLM** | Internal budget guards (503/queue) |

**Response on limit**

```json
{
  "error": {
    "code": "RATE_LIMITED",
    "message": "Too many analysis requests from this IP. Try again in 60 seconds.",
    "retry_after": 60
  }
}
```

Headers: `X-RateLimit-*`, `Retry-After`.

---

## 22. Security

### 22.1 OWASP API Top risks (selected)

| Risk | Control |
|---|---|
| Broken auth | JWT verification, key hashing, short TTL |
| BOLA | Authorize by org membership on every resource id |
| SSRF | URL Validation Engine on all outbound fetches |
| Injection | Parameterized SQL; no Cypher/SQL string concat |
| Excessive data | Omit `raw_output` by default |
| Mass assignment | Pydantic `extra=forbid` |
| Denial of service | Rate limits, body size caps, timeouts |

### 22.2 JWT

- Asymmetric keys (RS256/ES256) preferred in prod
- Rotate keys; include `kid`
- Audience/issuer checks

### 22.3 SSRF

Mandatory before crawl; see ENGINE_SPEC / SECURITY.md.

### 22.4 CORS

- Allowlist frontend origins (`https://sitepilot.ai`, preview apps)
- Credentials only when needed
- No `*` with cookies

### 22.5 CSRF

- Bearer-token SPA pattern reduces classic CSRF
- If cookie sessions introduced: SameSite + CSRF tokens required

### 22.6 Transport

TLS everywhere; HSTS on api.sitepilot.ai.

---

## 23. Implementation Roadmap

```mermaid
gantt
    title SitePilot AI — API Implementation Roadmap
    dateFormat  YYYY-MM-DD
    axisFormat  %b %d

    section Phase 1 Foundation
    FastAPI app + error envelope + health     :a1, 2026-08-01, 5d
    OpenAPI models + request IDs              :a2, after a1, 4d

    section Phase 2 Audit MVP
    POST/GET audits + status polling          :b1, after a2, 8d
    Report GET + PDF enqueue                  :b2, after b1, 7d
    Rate limit anonymous IP                   :b3, after b1, 3d

    section Phase 3 Engines & Findings
    Engines list/detail read APIs             :c1, after b2, 6d
    Findings + recommendations read APIs      :c2, after c1, 5d
    Category convenience endpoints            :c3, after c2, 4d

    section Phase 4 Auth & Tenancy
    Register/login/JWT                        :d1, after c3, 8d
    Orgs/projects/websites CRUD               :d2, after d1, 10d

    section Phase 5 Platform
    API keys + scopes                         :e1, after d2, 6d
    Monitoring endpoints                      :e2, after e1, 7d
    Webhooks                                  :e3, after e2, 7d
```

### Phase checklist

| Phase | Deliverables | Exit criteria |
|---|---|---|
| 1 | Health, errors, OpenAPI skeleton | `/docs` loads |
| 2 | Anonymous audit + report loop | E2E URL → report JSON |
| 3 | Engine/finding reads | Dashboard tabs wired |
| 4 | Auth + tenancy | Multi-user isolation tests green |
| 5 | Keys, monitoring, webhooks | Agency workflows unblocked |

### Contributor rules

1. New endpoints update this spec in the same PR  
2. Add OpenAPI examples + contract tests  
3. Map errors to §15 codes  
4. Enforce authz on every `{id}`  
5. Prefer `/audits` resource names (domain language)

> [!NOTE]
> **North star:** The API exposes **Audit Runs, Findings, Recommendations, and Reports** as clear resources — async where necessary, typed always, and never leaks raw engine internals by default.

---

<p align="center">
  <sub>SitePilot AI — API Specification — Internal Engineering Documentation — Confidential</sub>
</p>

# SitePilot AI — Engine Specification

**Your AI-powered Website Intelligence Platform.**

| | |
|---|---|
| **Document Type** | Engineering Specification (Engine Layer) |
| **Product** | SitePilot AI |
| **Document** | `ENGINE_SPEC.md` |
| **Part** | **1 + 2 (Complete)** |
| **Version** | 1.1.0 |
| **Status** | `Draft — Implementation Authority` |
| **Owner** | Platform Engineering |
| **Audience** | Backend Engineers, AI Systems Engineers, SRE, QA |
| **Last Updated** | 2026-07-12 |
| **Companion Docs** | [PRD.md](./PRD.md), [ARCHITECTURE.md](./ARCHITECTURE.md), [API_SPEC.md](./API_SPEC.md), [SECURITY.md](./SECURITY.md) |

> [!NOTE]
> This document is the **implementation authority** for SitePilot AI processing engines. When application code conflicts with this spec, update the code or open an RFC to change the spec. Do not silently diverge.

> [!WARNING]
> Engines must not call sibling engines directly. All orchestration flows through the **Pipeline Orchestrator**. Cross-engine coupling is a severity-1 architecture violation.

---

## Table of Contents

1. [Purpose](#1-purpose)
2. [Why Engine-Based Architecture](#2-why-engine-based-architecture)
3. [Complete System Pipeline](#3-complete-system-pipeline)
4. [Engine Standards](#4-engine-standards)
5. [Shared Contracts](#5-shared-contracts)
6. [Engine 1 — URL Validation Engine](#6-engine-1--url-validation-engine)
7. [Engine 2 — Crawler Engine](#7-engine-2--crawler-engine)
8. [Engine 3 — HTML Parser Engine](#8-engine-3--html-parser-engine)
9. [Engine 4 — SEO Intelligence Engine](#9-engine-4--seo-intelligence-engine)
10. [Engine 5 — Performance Engine](#10-engine-5--performance-engine)
11. [Engine 6 — Security Engine](#11-engine-6--security-engine)
12. [Engine 7 — Accessibility Engine](#12-engine-7--accessibility-engine)
13. [Part 2 — Intelligence, Assembly & Platform](#13-part-2--intelligence-assembly--platform)
14. [Engine 8 — Health Score Engine](#14-engine-8--health-score-engine)
15. [Engine 9 — Business Impact Engine](#15-engine-9--business-impact-engine)
16. [Engine 10 — ROI Engine](#16-engine-10--roi-engine)
17. [Engine 11 — Data Quality Engine](#17-engine-11--data-quality-engine)
18. [Engine 12 — AI Recommendation Engine](#18-engine-12--ai-recommendation-engine)
19. [Engine 13 — Report Builder Engine](#19-engine-13--report-builder-engine)
20. [Engine 14 — PDF Engine](#20-engine-14--pdf-engine)
21. [Inter-Engine Communication](#21-inter-engine-communication)
22. [Data Contracts](#22-data-contracts)
23. [Logging](#23-logging)
24. [Caching](#24-caching)
25. [Observability](#25-observability)
26. [Error Handling](#26-error-handling)
27. [Testing](#27-testing)
28. [Security](#28-security)
29. [Future Engines](#29-future-engines)
30. [Engine Design Principles](#30-engine-design-principles)
31. [Engineering Roadmap & Contributor Guidance](#31-engineering-roadmap--contributor-guidance)

---

## 1. Purpose

SitePilot AI analyzes any public website and produces a business-friendly health report. Technically, that product is **not** a monolith of analysis functions. It is a **pipeline of independent processing engines**.

Every engine:

| Dimension | Requirement |
|---|---|
| **Purpose** | One clear responsibility phrased as a verb + object |
| **Inputs** | Typed, versioned contracts — never raw ambient state |
| **Outputs** | Typed, versioned contracts — durable and introspectable |
| **Responsibilities** | Explicit in/out-of-scope boundaries |
| **Dependencies** | Declared (libraries, external APIs, upstream engines via orchestrator) |
| **Processing Steps** | Deterministic workflow that can be stepped in a debugger |
| **Algorithms** | Documented formulas, tables, and decision trees |
| **Error Handling** | Typed failure modes; no swallowed exceptions |
| **Validation Rules** | Pre- and post-conditions on every I/O boundary |
| **Performance Considerations** | Latency budgets, concurrency, caching |
| **Security Considerations** | SSRF, injection, PII, secret handling |
| **Logging** | Structured fields required for every run |
| **Testing Strategy** | Unit, contract, golden-file, and integration expectations |
| **Future Improvements** | Explicit backlog so scope creep has a parking lot |

This Part 1 specification covers the **collection and analysis engines** that turn a user-supplied URL into structured technical findings:

1. URL Validation Engine  
2. Crawler Engine  
3. HTML Parser Engine  
4. SEO Intelligence Engine  
5. Performance Engine  
6. Security Engine  
7. Accessibility Engine  

Part 2 covers scoring, business translation, AI, report assembly, PDF, and cross-cutting platform concerns.

---

## 2. Why Engine-Based Architecture

### 2.1 Problem with Monolithic Analyzers

A single `analyze(url)` function that crawls, parses, scores SEO, calls Lighthouse, checks headers, and prompts an LLM creates:

| Failure Mode | Consequence |
|---|---|
| Tangled ownership | No team can change SEO without risking Performance |
| Untestable surfaces | Fixture HTML cannot exercise PDF or AI without crawling live sites |
| Cascade failures | One flaky PSI call aborts the entire report |
| Opaque latency | Cannot attribute the 45s budget to a specific stage |
| Unsafe evolution | Prompt changes accidentally alter scoring |

### 2.2 Design Goals

| Goal | How engines achieve it |
|---|---|
| **Isolation** | Each engine is a package with a public `run(input) -> output` API |
| **Replaceability** | Swap PageSpeed Insights for a local-only Lighthouse path without touching SEO |
| **Parallelism** | SEO / Performance / Security / Accessibility run concurrently after parse |
| **Observability** | Per-engine spans, metrics, and structured logs |
| **Safe degradation** | Performance can fail soft; Security can still produce findings |
| **Contract stability** | Downstream engines consume schemas, not implementation details |
| **Testability** | Golden crawl artifacts drive every engine offline |

### 2.3 Non-Goals of the Engine Model

- Engines are **not** microservices by default. MVP runs in-process workers with clear module boundaries. Network-splitting engines is a future scaling option, not an MVP requirement.
- Engines are **not** allowed to share mutable global state.
- Engines are **not** allowed to write directly to the final report table except via Report Builder (Part 2).

> [!TIP]
> Prefer **packages + typed contracts + orchestrator** over premature microservice extraction. Extract a network boundary only when an engine's resource profile (CPU, browser, GPU) forces it.

---

## 3. Complete System Pipeline

### 3.1 End-to-End Flow

```mermaid
flowchart TD
    U[User URL] --> V[URL Validation Engine]
    V --> C[Crawler Engine]
    C --> P[HTML Parser Engine]
    P --> SEO[SEO Intelligence Engine]
    P --> PERF[Performance Engine]
    P --> SEC[Security Engine]
    P --> A11Y[Accessibility Engine]
    SEO --> HS[Health Score Engine]
    PERF --> HS
    SEC --> HS
    A11Y --> HS
    HS --> BI[Business Impact Engine]
    BI --> ROI[ROI Engine]
    ROI --> DQ[Data Quality Engine]
    DQ --> AI[AI Recommendation Engine]
    AI --> RB[Report Builder Engine]
    RB --> PDF[PDF Engine]
    RB --> FE[Frontend Dashboard]

    style U fill:#111827,stroke:#6366f1,color:#fff
    style HS fill:#111827,stroke:#22c55e,color:#fff
    style AI fill:#111827,stroke:#eab308,color:#fff
    style RB fill:#111827,stroke:#38bdf8,color:#fff
    style FE fill:#111827,stroke:#a78bfa,color:#fff
```

### 3.2 Linear Narrative

```
User URL
  → URL Validation Engine
  → Crawler Engine
  → HTML Parser Engine
  → SEO Intelligence Engine
  → Performance Engine
  → Security Engine
  → Accessibility Engine
  → Health Score Engine
  → Business Impact Engine
  → ROI Engine
  → Data Quality Engine
  → AI Recommendation Engine
  → Report Builder Engine
  → PDF Engine
  → Frontend Dashboard
```

### 3.3 Concurrency Model

| Stage | Execution Mode | Gate |
|---|---|---|
| URL Validation | Synchronous, fail-fast | Must succeed before job enqueue |
| Crawler | Async worker job | Requires validated URL |
| HTML Parser | Async, after crawl | Requires crawl artifact |
| SEO / Performance / Security / Accessibility | **Parallel** after parse | Join barrier before Health Score |
| Health Score → … → Report Builder | Sequential | Each depends on prior typed output |
| PDF | Async after report persist | Dashboard may render before PDF ready |
| Frontend Dashboard | Polls report status / fetches JSON | Does not block on PDF |

```mermaid
flowchart LR
    subgraph Parallel["Parallel Analysis Fan-Out"]
        SEO[SEO]
        PERF[Perf]
        SEC[Security]
        A11Y[A11y]
    end

    PARSE[HTML Parser] --> Parallel
    Parallel --> JOIN{{Join Barrier}}
    JOIN --> HS[Health Score]
```

### 3.4 Pipeline Orchestrator Responsibilities

| Responsibility | Detail |
|---|---|
| Job lifecycle | `pending → validating → crawling → analyzing → scoring → enriching → complete \| failed` |
| Fan-out / fan-in | Launch parallel engines; wait with per-engine timeouts |
| Partial failure policy | Soft-fail Performance; hard-fail Crawler / URL Validation |
| Artifact store | Persist intermediate JSON blobs keyed by `report_id` + `engine` + `schema_version` |
| Idempotency | Re-running a stage with the same input hash returns cached output when allowed |
| Cancellation | Honor job cancel; abort in-flight HTTP and browser work |

> [!WARNING]
> The orchestrator is the **only** component allowed to decide skip / retry / degrade policy. Engines report typed errors; they do not decide to skip siblings.

---

## 4. Engine Standards

Every engine in SitePilot AI **must** be documented and implemented against this template. Copy this section when authoring a new engine RFC.

### 4.1 Documentation Template

#### Purpose

One paragraph. What business or technical outcome does this engine produce?

#### Responsibilities

| In Scope | Out of Scope |
|---|---|
| … | … |

#### Inputs

| Field | Type | Required | Description |
|---|---|---|---|
| … | … | yes/no | … |

Schema version: `engine.<name>.input.vN`

#### Outputs

| Field | Type | Description |
|---|---|---|
| … | … | … |

Schema version: `engine.<name>.output.vN`

#### Dependencies

| Dependency | Kind | Notes |
|---|---|---|
| Upstream engine outputs | Contract | Via orchestrator only |
| External API | Network | Timeouts, quotas |
| Library | In-process | Pin versions |

#### Internal Workflow

Numbered steps. Prefer a Mermaid flowchart.

#### Algorithms

Formulas, decision tables, severity maps.

#### Validation Rules

Pre-conditions (reject bad input) and post-conditions (reject bad self-output).

#### Failure Handling

| Error Code | Retryable | Effect on Pipeline |
|---|---|---|
| … | yes/no | hard-fail / soft-fail / degrade |

#### Caching

Key, TTL, invalidation rules.

#### Logging

Required structured fields.

#### Security

Threat model notes for this engine.

#### Performance

Latency budget (p50 / p95), concurrency limits.

#### Testing

Unit, contract, golden fixtures, integration.

#### Future Improvements

Parked ideas — not MVP scope.

### 4.2 Implementation Contract (Code)

Every engine package exposes:

```text
apps/api/app/engines/<engine_name>/
├── __init__.py
├── engine.py              # run(ctx, input) -> Output
├── schemas.py             # Pydantic Input / Output / Error
├── rules.py               # Pure decision tables where applicable
├── errors.py              # Typed engine errors
└── tests/
    ├── test_unit.py
    ├── test_contracts.py
    └── fixtures/
```

**Required function signature (conceptual):**

```python
def run(ctx: EngineContext, payload: EngineInput) -> EngineOutput:
    """
    Pure-ish entrypoint. Side effects (HTTP, browser, LLM) only via injected clients.
    Must not import sibling engines.
    """
```

| `EngineContext` Field | Purpose |
|---|---|
| `report_id` | Correlation ID |
| `job_id` | Worker job ID |
| `trace_id` | Distributed trace |
| `config` | Feature flags + engine config snapshot |
| `clock` | Injectable time for tests |
| `http` / `browser` / `llm` | Injected clients |
| `logger` | Bound structured logger |
| `cache` | Optional cache adapter |

### 4.3 Standard Output Envelope

All engine outputs wrap findings in a common envelope:

```json
{
  "engine": "seo_intelligence",
  "schema_version": "engine.seo.output.v1",
  "report_id": "rep_9f3ac21e",
  "status": "success",
  "duration_ms": 842,
  "warnings": [],
  "data": {},
  "meta": {
    "config_version": "scoring_config@3",
    "started_at": "2026-07-12T10:15:01.200Z",
    "finished_at": "2026-07-12T10:15:02.042Z"
  }
}
```

| `status` | Meaning |
|---|---|
| `success` | Full output produced |
| `partial` | Degraded output; warnings explain gaps |
| `failed` | No usable `data`; pipeline applies failure policy |

### 4.4 Standard Finding Object

Analysis engines (SEO, Performance, Security, Accessibility) emit findings of this shape:

```json
{
  "id": "seo.meta_description.missing",
  "category": "seo",
  "check": "meta_description",
  "status": "fail",
  "severity": "high",
  "confidence": 100,
  "title": "Missing Meta Description",
  "technical_detail": "No <meta name='description'> tag found in <head>.",
  "evidence": {
    "selector": "head > meta[name=description]",
    "observed": null,
    "expected": "50-160 character meta description"
  },
  "tags": ["metadata", "serp"],
  "wcag": null,
  "docs_url": null
}
```

| Field | Rules |
|---|---|
| `id` | Stable, namespaced, never rename casually (`category.check.variant`) |
| `severity` | `critical` \| `high` \| `medium` \| `low` \| `info` |
| `confidence` | Integer 0–100; deterministic checks default to 100 |
| `status` | `pass` \| `fail` \| `warn` \| `skip` \| `error` |
| `evidence` | Must be machine-readable; used by AI and UI |

### 4.5 Standard Error Object

```json
{
  "engine": "crawler",
  "error": {
    "code": "CRAWL_TIMEOUT",
    "message": "Origin did not respond within 10000ms",
    "retryable": true,
    "details": {
      "url": "https://example.com",
      "timeout_ms": 10000
    }
  }
}
```

### 4.6 Latency Budgets (MVP Targets)

| Engine | p50 | p95 | Hard Timeout |
|---|---|---|---|
| URL Validation | 50ms | 300ms | 5s (includes HEAD) |
| Crawler | 800ms | 3s | 10s |
| HTML Parser | 40ms | 150ms | 2s |
| SEO Intelligence | 100ms | 400ms | 5s |
| Performance | 8s | 25s | 30s |
| Security | 80ms | 300ms | 5s |
| Accessibility | 120ms | 500ms | 5s |
| **End-to-end analysis** | ≤ 20s | ≤ 45s | 60s job ceiling |

> [!NOTE]
> Performance Engine dominates the budget. All other analysis engines must remain cheap enough to run in parallel without extending wall-clock time beyond Performance.

---

## 5. Shared Contracts

### 5.1 Validated URL Object

Produced by URL Validation; consumed by Crawler.

```json
{
  "raw_url": "example.com",
  "normalized_url": "https://example.com/",
  "canonical_url": "https://example.com/",
  "scheme": "https",
  "host": "example.com",
  "port": 443,
  "path": "/",
  "resolved_ips": ["93.184.216.34"],
  "https": true,
  "reachable": true,
  "reachability_status_code": 200,
  "validation_warnings": []
}
```

### 5.2 Crawl Artifact Object

Produced by Crawler; consumed by Parser, Security (headers), Performance (URL), SEO (robots/sitemap).

```json
{
  "final_url": "https://example.com/",
  "requested_url": "https://example.com/",
  "status_code": 200,
  "redirect_chain": [],
  "headers": {
    "content-type": "text/html; charset=utf-8",
    "server": "ECS"
  },
  "html": "<!doctype html>...",
  "html_bytes": 12840,
  "encoding": "utf-8",
  "timing": {
    "dns_ms": 12,
    "connect_ms": 40,
    "ttfb_ms": 180,
    "download_ms": 35,
    "total_ms": 255
  },
  "robots_txt": {
    "present": true,
    "url": "https://example.com/robots.txt",
    "body": "User-agent: *\nAllow: /"
  },
  "sitemap": {
    "present": true,
    "urls": ["https://example.com/sitemap.xml"]
  },
  "tls": {
    "used": true,
    "valid": true,
    "expires_at": "2027-01-01T00:00:00Z",
    "issuer": "Example CA"
  }
}
```

### 5.3 Parsed Document Object

Produced by HTML Parser; primary input for SEO / Accessibility (and evidence for Security mixed-content checks).

See [Engine 3](#8-engine-3--html-parser-engine) for full schema.

---

## 6. Engine 1 — URL Validation Engine

### 6.1 Purpose

Accept a user-supplied URL string and produce a **safe, normalized, reachable** URL object — or a typed rejection — **before** any expensive crawl, browser, or AI work begins.

This engine is the first line of defense against SSRF, malformed input, and wasted compute.

### 6.2 Responsibilities

| In Scope | Out of Scope |
|---|---|
| Syntax validation | Full page crawl |
| Scheme enforcement (`http` / `https` only) | HTML parsing |
| Normalization & canonicalization | Lighthouse / PSI |
| DNS resolution + private IP blocking (SSRF) | Content analysis |
| Optional reachability `HEAD`/`GET` probe | Rate-limit persistence (uses shared limiter) |
| HTTPS presence signaling | Certificate deep audit (Security Engine) |

### 6.3 Inputs

| Field | Type | Required | Description |
|---|---|---|---|
| `url` | string | yes | User-provided URL (may omit scheme) |
| `client_ip` | string | yes | For rate limiting / abuse logs |
| `options.skip_reachability` | boolean | no | Test-only / cache-replay |
| `options.timeout_ms` | int | no | Override probe timeout (default 5000) |

**Schema:** `engine.url_validation.input.v1`

### 6.4 Outputs

**Success — `engine.url_validation.output.v1`**

```json
{
  "engine": "url_validation",
  "schema_version": "engine.url_validation.output.v1",
  "report_id": "rep_9f3ac21e",
  "status": "success",
  "duration_ms": 186,
  "data": {
    "raw_url": "Example.COM/path",
    "normalized_url": "https://example.com/path",
    "canonical_url": "https://example.com/path",
    "scheme": "https",
    "host": "example.com",
    "port": 443,
    "path": "/path",
    "query": "",
    "fragment_stripped": true,
    "resolved_ips": ["93.184.216.34"],
    "https": true,
    "reachable": true,
    "reachability_method": "HEAD",
    "reachability_status_code": 200,
    "validation_warnings": []
  }
}
```

**Error — example**

```json
{
  "engine": "url_validation",
  "status": "failed",
  "error": {
    "code": "SSRF_BLOCKED",
    "message": "Resolved address is not a public internet target.",
    "retryable": false,
    "details": {
      "host": "localhost",
      "resolved_ips": ["127.0.0.1"]
    }
  }
}
```

### 6.5 Supported URLs

| Case | Supported | Notes |
|---|---|---|
| `https://example.com` | Yes | Preferred |
| `http://example.com` | Yes | Allowed; flag `https: false` |
| `example.com` | Yes | Auto-prepend `https://` |
| `https://example.com:8443/path?x=1` | Yes | Non-default ports allowed if public |
| `ftp://…`, `file://…`, `data:` | **No** | Reject `INVALID_SCHEME` |
| Internationalized domains | Yes | Punycode normalize (IDNA) |
| IP-literal hosts (`http://1.2.3.4`) | Conditional | Only if public unicast; still SSRF-checked |

### 6.6 Normalization

Apply in order:

1. Trim whitespace.
2. If scheme missing, prepend `https://`.
3. Lowercase scheme and host.
4. IDNA-encode host (Unicode → punycode).
5. Remove default ports (`:80` for http, `:443` for https).
6. Collapse empty path to `/` for origin-only URLs when canonicalizing for cache keys.
7. Strip URL fragments (`#…`) — fragments are never sent to servers.
8. Preserve query string as provided (do not reorder in MVP).
9. Reject credentials in URL (`https://user:pass@host`) → `CREDENTIALS_NOT_ALLOWED`.

### 6.7 Canonicalization

Canonical URL is used for **cache keys** and report identity:

| Rule | Behavior |
|---|---|
| Trailing slash on bare origin | Force `https://example.com/` |
| `www` vs apex | Do **not** rewrite in MVP; treat as distinct hosts |
| HTTP vs HTTPS | Distinct; do not auto-upgrade beyond initial prepend |
| Tracking params | Do **not** strip in MVP (document as future improvement) |

### 6.8 HTTPS Validation

| Check | Result |
|---|---|
| Scheme is `https` | `https: true` |
| Scheme is `http` | `https: false` + warning `HTTP_NOT_HTTPS` |
| TLS handshake during reachability | Soft signal only; deep cert validation belongs to Security Engine |

### 6.9 Reachability

| Step | Detail |
|---|---|
| Method | Prefer `HEAD`; fall back to `GET` with `Range: bytes=0-0` if `HEAD` returns 405/501 |
| Timeout | Default **5s** total |
| Success | Any HTTP response from origin after SSRF checks (including 3xx/4xx/5xx) proves reachability of a public host |
| Failure | Timeout, DNS failure, connection refused → `UNREACHABLE` |
| Redirects | Follow ≤ 3 redirects during probe; each hop re-validated for SSRF |

> [!NOTE]
> A `404` during reachability still means the host is reachable. Analysis may continue; SEO/Crawler interpret status codes later.

### 6.10 Timeout Handling

| Timeout | Value | Action |
|---|---|---|
| DNS | 2s | `DNS_FAILURE` |
| TCP connect | 3s | `UNREACHABLE` |
| Total probe | 5s | `UNREACHABLE` |
| Engine wall | 5s | Fail closed |

### 6.11 Rate Limiting

| Dimension | Default MVP |
|---|---|
| Per `client_ip` | 5 validations that proceed to analysis / 10 minutes |
| Per host | 30 crawls / hour globally (shared with Crawler) |
| Burst | Token bucket; return `RATE_LIMITED` with `retry_after` |

Rate limiting is **enforced at API gateway + validation engine**. Validation engine must call the shared limiter before DNS/reachability when the request would enqueue work.

### 6.12 Input Validation Rules

| Rule | Error Code |
|---|---|
| Empty / whitespace-only | `URL_REQUIRED` |
| Length > 2048 chars | `URL_TOO_LONG` |
| Invalid URL syntax | `INVALID_URL` |
| Disallowed scheme | `INVALID_SCHEME` |
| Userinfo present | `CREDENTIALS_NOT_ALLOWED` |
| Host missing | `INVALID_URL` |

### 6.13 SSRF Prevention

> [!WARNING]
> SSRF protection is mandatory on **every** DNS resolution and redirect hop. This product fetches arbitrary user URLs by design — it is a textbook SSRF surface.

| Control | Implementation |
|---|---|
| Resolve DNS before connect | Use explicit resolver; pin connection to resolved IPs |
| Block private/reserved ranges | `10.0.0.0/8`, `172.16.0.0/12`, `192.168.0.0/16`, `127.0.0.0/8`, `169.254.0.0/16`, `::1`, `fc00::/7`, `fe80::/10` |
| Block metadata endpoints | `169.254.169.254`, link-local cloud metadata hostnames |
| Block hostnames | `localhost`, `*.local`, internal corp suffixes from config denylist |
| Re-check redirects | Re-resolve and re-validate each `Location` host |
| No DNS rebinding window | Connect using first-resolution IPs; do not trust later TTL changes mid-request |

### 6.14 Dependencies

| Dependency | Kind |
|---|---|
| Shared SSRF guard (`core/security.py`) | In-process |
| Shared rate limiter (Redis) | Network |
| DNS resolver / httpx probe client | Network |

### 6.15 Internal Workflow

```mermaid
flowchart TD
    A[Receive url + client_ip] --> B{Non-empty & length OK?}
    B -- No --> E1[Fail INVALID_URL / URL_TOO_LONG]
    B -- Yes --> C[Normalize + canonicalize]
    C --> D{Scheme http/https?}
    D -- No --> E2[Fail INVALID_SCHEME]
    D -- Yes --> F{Credentials present?}
    F -- Yes --> E3[Fail CREDENTIALS_NOT_ALLOWED]
    F -- No --> G{Rate limit OK?}
    G -- No --> E4[Fail RATE_LIMITED]
    G -- Yes --> H[DNS resolve]
    H --> I{Public IPs only?}
    I -- No --> E5[Fail SSRF_BLOCKED]
    I -- Yes --> J[Reachability probe]
    J --> K{Reachable?}
    K -- No --> E6[Fail UNREACHABLE]
    K -- Yes --> L[Emit Validated URL JSON]
```

### 6.16 Processing Steps (Detailed)

1. Bind logger with `report_id`, `client_ip`.
2. Validate string constraints.
3. Normalize and canonicalize.
4. Enforce scheme + reject credentials.
5. Check rate limits.
6. Resolve DNS; run SSRF IP checks.
7. Perform reachability probe with hop-by-hop SSRF.
8. Emit success output or typed error.
9. Log duration, host, result code.

### 6.17 Algorithms

**Auto-scheme:**

```
if url has no scheme:
  candidate = "https://" + url
else:
  candidate = url
```

**SSRF decision:**

```
for each resolved IP:
  if IP in blocked_ranges OR host in denylist:
    reject SSRF_BLOCKED
allow
```

### 6.18 Failure Handling

| Code | Retryable | Pipeline Effect |
|---|---|---|
| `URL_REQUIRED` | no | Hard-fail; do not enqueue |
| `INVALID_URL` | no | Hard-fail |
| `INVALID_SCHEME` | no | Hard-fail |
| `CREDENTIALS_NOT_ALLOWED` | no | Hard-fail |
| `SSRF_BLOCKED` | no | Hard-fail; security log |
| `RATE_LIMITED` | yes | Hard-fail request; client retries later |
| `DNS_FAILURE` | yes | Hard-fail |
| `UNREACHABLE` | yes | Hard-fail |

### 6.19 Caching

| Key | `url_validation:v1:{canonical_url}` |
|---|---|
| TTL | 15 minutes for successful validations |
| Negative cache | 2 minutes for `UNREACHABLE` / `DNS_FAILURE` (not for SSRF) |
| Invalidation | Manual or TTL expiry |

### 6.20 Logging

Required fields: `engine`, `report_id`, `raw_url`, `canonical_url`, `host`, `client_ip`, `result`, `error_code`, `duration_ms`, `resolved_ip_count`.

Never log full query strings if they may contain secrets (redact known secret param names).

### 6.21 Security Considerations

- Treat all input as hostile.
- Never fetch before SSRF checks.
- Emit security telemetry on `SSRF_BLOCKED`.
- Do not return internal IP details to end users in public error messages (keep in `details` for internal logs only if needed; public API uses generic message).

### 6.22 Performance Considerations

- Keep path CPU-bound + one short probe.
- Reuse HTTP keep-alive pools carefully; do not share sockets across untrusted hosts without isolation.
- Prefer fail-fast ordering: syntax → SSRF → probe.

### 6.23 Testing Strategy

| Test Type | Examples |
|---|---|
| Unit | Normalization matrix, IDNA, fragment strip |
| SSRF fixtures | localhost, 10.x, metadata IP, DNS rebinding redirect fixtures |
| Contract | Output schema validation |
| Integration | Live `example.com` reachability in sandbox CI only |

### 6.24 Future Improvements

- Strip common tracking parameters for canonical cache keys.
- Optional `www` apex equivalence option per tenant.
- Passive-based allow/deny for Enterprise.
- QUIC / HTTP3 probe metrics.

---

## 7. Engine 2 — Crawler Engine

### 7.1 Purpose

Fetch a validated public URL and return a **normalized crawl artifact**: final HTML, response headers, redirect chain, timing, TLS summary, `robots.txt`, and sitemap discovery hints — safely and reproducibly.

### 7.2 Responsibilities

| In Scope | Out of Scope |
|---|---|
| HTTP(S) GET of target document | DOM semantic analysis |
| Redirect following with SSRF re-check | Lighthouse execution |
| Response size caps | Business scoring |
| `robots.txt` fetch | Full site spider (MVP is single-page) |
| Sitemap discovery (best-effort) | Authenticated crawling |
| Error recovery / retries | Writing final reports |

### 7.3 Inputs

| Field | Type | Required | Description |
|---|---|---|---|
| `validated_url` | Validated URL object | yes | From URL Validation Engine |
| `options.max_redirects` | int | no | Default 5 |
| `options.timeout_ms` | int | no | Default 10000 |
| `options.max_bytes` | int | no | Default 10_000_000 |
| `options.fetch_robots` | bool | no | Default true |
| `options.fetch_sitemap` | bool | no | Default true |

**Schema:** `engine.crawler.input.v1`

### 7.4 Dependencies

| Dependency | Kind |
|---|---|
| URL Validation output | Upstream contract |
| httpx (async) | HTTP client |
| Shared SSRF guard | Security |
| Redis cache | Optional artifact cache |
| TLS stack | Certificate summary |

### 7.5 HTTP Requests

| Setting | MVP Default |
|---|---|
| Method | `GET` |
| HTTP versions | HTTP/1.1 and HTTP/2 as negotiated |
| Accept | `text/html,application/xhtml+xml;q=0.9,*/*;q=0.8` |
| Accept-Language | `en-US,en;q=0.9` |
| Accept-Encoding | `gzip, deflate, br` |
| Connection | keep-alive within per-host pool |
| Max response body | 10MB hard cap |
| Stream read | Stream until cap; abort with `RESPONSE_TOO_LARGE` |

### 7.6 Redirect Handling

| Rule | Behavior |
|---|---|
| Max redirects | 5 |
| Schemes | Only `http`/`https` |
| SSRF | Re-validate every hop |
| Cross-host redirects | Allowed if public |
| Cross-scheme `http→https` | Allowed; record in chain |
| Loops | Detect by URL set; fail `REDIRECT_LOOP` |
| Missing `Location` | Fail `INVALID_REDIRECT` |

Redirect chain entry:

```json
{
  "from": "http://example.com/",
  "to": "https://example.com/",
  "status_code": 301
}
```

### 7.7 Retry Logic

| Condition | Retries | Backoff |
|---|---|---|
| Connect timeout / reset | 2 | 200ms, 800ms (+ jitter) |
| HTTP 502 / 503 / 504 | 2 | Same |
| HTTP 429 | 1 | Honor `Retry-After` if ≤ 5s, else fail |
| HTTP 4xx (except 429) | 0 | Fail / continue per policy |
| SSRF / size / scheme errors | 0 | Never retry |

### 7.8 User Agent Strategy

```
User-Agent: SitePilotBot/1.0 (+https://sitepilot.ai/bot; reports@sitepilot.ai)
```

| Principle | Detail |
|---|---|
| Identify honestly | Do not spoof Chrome for MVP HTML fetch |
| Contact URL | Required for operator trust |
| Separate UA for Playwright | Performance Engine may use browser UA — not this engine |

### 7.9 robots.txt

| Step | Detail |
|---|---|
| Fetch | `GET {origin}/robots.txt` with 5s timeout |
| Parse | Record raw body; MVP does not block single-page analysis solely on `Disallow` |
| Policy | Log if `Disallow: /` would block SitePilotBot; still proceed for MVP audit product with warning `ROBOTS_DISALLOW_ALL` |
| Failure | Missing robots → `present: false` (not an engine failure) |

> [!NOTE]
> Product decision (MVP): SitePilot AI performs an **on-demand single-page audit** initiated by a user who controls or is evaluating the site. We still fetch and surface robots data, but we do not hard-stop on Disallow for the primary URL. Revisit for continuous monitoring crawlers in V2.

### 7.10 Sitemap Discovery

Discovery order:

1. Parse `Sitemap:` directives from robots.txt  
2. Probe `/sitemap.xml`  
3. Probe `/sitemap_index.xml`  

Record URLs found; do **not** download entire sitemap indexes beyond a 1MB cap in MVP.

### 7.11 Caching

| Key | `crawl:v1:{sha256(canonical_url)}` |
|---|---|
| TTL | 24h (aligns with report cache) |
| Store | HTML + headers + robots/sitemap metadata (not unbounded sitemaps) |
| Bypass | `Cache-Control` force refresh flag on API (admin / future Pro) |

### 7.12 Distributed Crawling (Future)

| Capability | Status |
|---|---|
| Multi-page BFS crawl | Future |
| Domain-sharded workers | Future |
| Crawl frontier queue | Future |
| Per-host politeness delay | Design now: 1 req/s/host default when multi-page lands |

### 7.13 Timeouts

| Phase | Timeout |
|---|---|
| DNS + connect | 3s |
| TTFB | 5s |
| Total body download | 10s |
| robots.txt | 5s |
| sitemap probe | 5s each |
| Engine wall clock | 15s including robots/sitemap |

### 7.14 Headers (Captured)

Always capture (lowercased keys):

- `content-type`, `content-length`, `server`, `x-powered-by`
- `strict-transport-security`, `content-security-policy`, `x-frame-options`
- `x-content-type-options`, `referrer-policy`, `permissions-policy`
- `cache-control`, `set-cookie` (**redact values in logs**)
- `location` (on redirects)

### 7.15 Error Recovery

| Error | Recovery |
|---|---|
| Truncated HTML at size cap | Soft-fail with `partial` status if ≥ 1KB received; warning `HTML_TRUNCATED` |
| Non-HTML content-type | Fail `UNSUPPORTED_CONTENT_TYPE` unless body sniffs as HTML |
| Empty body | Fail `EMPTY_BODY` |
| TLS error | Fail `TLS_ERROR` (Security will not run without crawl; pipeline hard-fail) |

### 7.16 Mermaid Sequence Diagram

```mermaid
sequenceDiagram
    participant Orch as Orchestrator
    participant Crawl as Crawler Engine
    participant SSRF as SSRF Guard
    participant Origin as Target Origin
    participant Cache as Redis Cache

    Orch->>Crawl: run(validated_url)
    Crawl->>Cache: GET crawl:v1:hash
    alt cache hit
        Cache-->>Crawl: crawl artifact
        Crawl-->>Orch: success (cache)
    else cache miss
        Crawl->>SSRF: assert_public(host)
        SSRF-->>Crawl: ok
        Crawl->>Origin: GET page
        Origin-->>Crawl: 301 Location
        Crawl->>SSRF: assert_public(redirect host)
        Crawl->>Origin: GET final
        Origin-->>Crawl: 200 HTML + headers
        Crawl->>Origin: GET /robots.txt
        Origin-->>Crawl: robots body
        Crawl->>Origin: GET /sitemap.xml
        Origin-->>Crawl: sitemap or 404
        Crawl->>Cache: SET artifact TTL=24h
        Crawl-->>Orch: crawl artifact
    end
```

### 7.17 Output JSON Schema

```json
{
  "engine": "crawler",
  "schema_version": "engine.crawler.output.v1",
  "report_id": "rep_9f3ac21e",
  "status": "success",
  "duration_ms": 1104,
  "warnings": [],
  "data": {
    "requested_url": "https://example.com/",
    "final_url": "https://example.com/",
    "status_code": 200,
    "redirect_chain": [],
    "headers": {
      "content-type": "text/html; charset=utf-8"
    },
    "html": "<!doctype html><html>...</html>",
    "html_bytes": 12840,
    "encoding": "utf-8",
    "timing": {
      "dns_ms": 12,
      "connect_ms": 40,
      "ttfb_ms": 180,
      "download_ms": 35,
      "total_ms": 255
    },
    "robots_txt": {
      "present": true,
      "url": "https://example.com/robots.txt",
      "body": "User-agent: *\nAllow: /\nSitemap: https://example.com/sitemap.xml",
      "sitemaps_declared": ["https://example.com/sitemap.xml"],
      "disallow_all_for_bot": false
    },
    "sitemap": {
      "present": true,
      "urls": ["https://example.com/sitemap.xml"],
      "probed": ["/sitemap.xml"]
    },
    "tls": {
      "used": true,
      "valid": true,
      "expires_at": "2027-01-01T00:00:00Z",
      "issuer": "Example CA"
    },
    "user_agent": "SitePilotBot/1.0 (+https://sitepilot.ai/bot; reports@sitepilot.ai)"
  }
}
```

### 7.18 Validation Rules

**Pre:** `validated_url.reachable == true` and SSRF already passed.  
**Post:** `html_bytes ≤ max_bytes`; `final_url` scheme http/https; headers dict present; encoding detected or defaulted to utf-8 with warning.

### 7.19 Failure Handling

| Code | Retryable | Pipeline |
|---|---|---|
| `CRAWL_TIMEOUT` | yes | Hard-fail |
| `RESPONSE_TOO_LARGE` | no | Hard-fail |
| `UNSUPPORTED_CONTENT_TYPE` | no | Hard-fail |
| `EMPTY_BODY` | no | Hard-fail |
| `REDIRECT_LOOP` | no | Hard-fail |
| `TLS_ERROR` | yes | Hard-fail |
| `SSRF_BLOCKED` | no | Hard-fail |

### 7.20 Logging

`engine`, `report_id`, `requested_url`, `final_url`, `status_code`, `redirect_count`, `html_bytes`, `cache_hit`, `duration_ms`, `warning_codes`.

Do not log raw HTML bodies at info level.

### 7.21 Security Considerations

- SSRF on every hop.
- Size caps prevent memory exhaustion.
- Redact `set-cookie` values in logs.
- Strip hop-by-hop headers when forwarding internally.

### 7.22 Performance Considerations

- Cache hits should return in < 20ms.
- Stream parse encoding detection without loading unbounded data.
- robots/sitemap probes run sequentially after primary fetch to avoid thundering herd on fragile origins; total must fit wall clock.

### 7.23 Testing Strategy

| Type | Focus |
|---|---|
| Unit | Redirect loop detection, size cap, header normalization |
| Contract | Output schema |
| Integration | Wiremock / httpbin fixtures |
| Security | Redirect-to-localhost attempts must fail |

### 7.24 Future Improvements

- Multi-page crawl with politeness.
- Conditional requests (`ETag` / `If-Modified-Since`).
- Headless render capture shared with Performance (single browser session).
- HTTP/3 metrics.

---

## 8. Engine 3 — HTML Parser Engine

### 8.1 Purpose

Transform raw HTML from the Crawler into a **structured Parsed Document** that downstream engines can consume without re-parsing markup. This engine owns DOM interpretation consistency across SEO, Accessibility, and mixed-content checks.

### 8.2 Responsibilities

| In Scope | Out of Scope |
|---|---|
| HTML parse via BeautifulSoup + lxml | Network I/O |
| Metadata extraction | Scoring / penalties |
| Headings, links, images, scripts, forms | Executing JavaScript |
| Charset handling | Pixel contrast measurement (Accessibility may refine) |
| Structured JSON emission | Mutating crawl artifact |

### 8.3 Inputs

| Field | Type | Required |
|---|---|---|
| `crawl` | Crawl artifact | yes |
| `options.max_nodes` | int | no (default 200_000) |
| `options.max_links` | int | no (default 5_000) |

**Schema:** `engine.html_parser.input.v1`

### 8.4 Dependencies

| Library | Role |
|---|---|
| **BeautifulSoup** | Ergonomic DOM traversal API |
| **lxml** | Fast underlying parser (`html.parser` fallback if lxml fails) |
| Crawler output | Upstream |

> [!TIP]
> Prefer `BeautifulSoup(html, "lxml")`. Fall back to `html.parser` on lxml failure and emit warning `PARSER_FALLBACK`.

### 8.5 DOM Processing

| Step | Detail |
|---|---|
| 1 | Decode bytes using declared charset / chardet fallback |
| 2 | Parse into DOM |
| 3 | If node count exceeds `max_nodes`, truncate traversal and warn `DOM_TRUNCATED` |
| 4 | Extract sections below into typed arrays |
| 5 | Compute simple stats (counts, empty alts, etc.) |

### 8.6 Metadata Extraction

Extract:

| Field | Source |
|---|---|
| `title` | `<title>` |
| `meta_description` | `<meta name="description" content>` |
| `canonical` | `<link rel="canonical" href>` |
| `robots_meta` | `<meta name="robots" content>` |
| `viewport` | `<meta name="viewport" content>` |
| `charset` | `<meta charset>` or http-equiv |
| `lang` | `<html lang>` |
| `favicon` | `<link rel="icon">` etc. |
| Open Graph | `og:*` meta properties |
| Twitter | `twitter:*` meta names |
| JSON-LD | `<script type="application/ld+json">` raw + parse attempt |

### 8.7 Heading Extraction

```json
{
  "level": 1,
  "text": "Welcome",
  "order": 0
}
```

Rules:

- Capture `h1`–`h6` in document order.
- Collapse whitespace in text.
- Truncate text to 300 chars with flag `truncated: true`.

### 8.8 Image Extraction

```json
{
  "src": "/hero.jpg",
  "alt": null,
  "alt_missing": true,
  "loading": "lazy",
  "width": null,
  "height": null
}
```

### 8.9 Link Extraction

```json
{
  "href": "https://example.com/about",
  "text": "About",
  "rel": [],
  "nofollow": false,
  "internal": true,
  "kind": "anchor"
}
```

Classification:

- **Internal:** same registrable domain as `final_url`
- **External:** otherwise
- Skip `mailto:`, `tel:`, `javascript:` from link graph counts (record separately)

### 8.10 Script Extraction

Record `src`, `async`, `defer`, `type`, inline-or-external boolean. Do **not** store full inline script bodies in persisted artifacts (hash + length only) to reduce PII/secret leakage.

### 8.11 Form Extraction

```json
{
  "action": "/search",
  "method": "get",
  "inputs": [
    { "type": "text", "name": "q", "id": "q", "has_label": true }
  ]
}
```

`has_label` is true if a `<label for=id>` exists or input is wrapped by `<label>`.

### 8.12 Structured Output

**Schema:** `engine.html_parser.output.v1`

```json
{
  "engine": "html_parser",
  "schema_version": "engine.html_parser.output.v1",
  "report_id": "rep_9f3ac21e",
  "status": "success",
  "duration_ms": 48,
  "warnings": [],
  "data": {
    "base_url": "https://example.com/",
    "metadata": {
      "title": "Example Domain",
      "meta_description": null,
      "canonical": "https://example.com/",
      "robots_meta": null,
      "lang": "en",
      "viewport": "width=device-width, initial-scale=1",
      "favicon": "/favicon.ico",
      "open_graph": {
        "og:title": null,
        "og:description": null,
        "og:image": null
      },
      "twitter": {
        "twitter:card": null,
        "twitter:title": null
      },
      "json_ld": []
    },
    "headings": [
      { "level": 1, "text": "Example Domain", "order": 0 }
    ],
    "images": [],
    "links": {
      "internal": [],
      "external": [],
      "counts": { "internal": 0, "external": 0, "nofollow": 0 }
    },
    "scripts": {
      "external_count": 0,
      "inline_count": 0,
      "items": []
    },
    "forms": [],
    "stats": {
      "node_count": 42,
      "images_total": 0,
      "images_missing_alt": 0,
      "h1_count": 1
    }
  }
}
```

### 8.13 Output JSON Examples — Edge Cases

**Malformed HTML still parseable:**

```json
{
  "status": "partial",
  "warnings": [
    { "code": "PARSER_FALLBACK", "message": "lxml failed; used html.parser" }
  ]
}
```

**Huge DOM:**

```json
{
  "status": "partial",
  "warnings": [
    { "code": "DOM_TRUNCATED", "message": "Stopped traversal after 200000 nodes" }
  ]
}
```

### 8.14 Algorithms

**Internal link check (MVP):**

```
internal = (link_host == final_host) OR (link_host == "" AND relative href)
```

**Label association:**

```
has_label =
  exists label[for=input.id]
  OR input is descendant of label
  OR aria-label / aria-labelledby present
```

### 8.15 Validation Rules

- Reject empty HTML string.
- Post-condition: `metadata` object always present (fields nullable).
- Link arrays length ≤ `max_links`.

### 8.16 Failure Handling

| Code | Pipeline |
|---|---|
| `PARSE_FAILED` | Hard-fail (downstream analyzers cannot run) |
| `DOM_TRUNCATED` | Soft (`partial`) |
| `PARSER_FALLBACK` | Soft |

### 8.17 Caching / Logging / Security / Performance

| Concern | Rule |
|---|---|
| Caching | Optional; key off crawl content hash |
| Logging | Counts only; never full DOM |
| Security | Do not execute scripts; strip/ignore event handlers |
| Performance | O(n) traversal; avoid quadratic BeautifulSoup queries in hot loops |

### 8.18 Testing Strategy

- Fixture HTML corpus: missing title, multiple h1, SVG images, malformed tags, JSON-LD arrays vs objects.
- Golden JSON snapshots per fixture.
- Property test: parser never throws on arbitrary byte strings (returns failed/partial).

### 8.19 Future Improvements

- Readability main-content extraction.
- Shadow DOM / hydrated content via shared browser snapshot.
- CSS selector evidence richer paths for UI deep links.

---

## 9. Engine 4 — SEO Intelligence Engine

### 9.1 Purpose

Evaluate on-page and crawl-adjacent SEO signals and emit **typed SEO findings** with severity, confidence, evidence, and check identifiers suitable for scoring and business translation.

### 9.2 Responsibilities

| In Scope | Out of Scope |
|---|---|
| Title, meta, canonical, robots, sitemap checks | Keyword rank tracking (future) |
| OG / Twitter / Schema checks | Backlink indexes |
| Heading hierarchy & ALT coverage | Full-site duplicate detection across uncrawled pages |
| Broken link sampling for extracted internal links | Content quality NLP scoring |
| Penalty inputs for Health Score | Writing AI copy |

### 9.3 Inputs

| Field | Source |
|---|---|
| `parsed` | HTML Parser output |
| `crawl` | Crawler output (status, robots, sitemap) |
| `options.check_broken_links` | bool (default true) |
| `options.broken_link_sample_size` | int (default 25) |

**Schema:** `engine.seo.input.v1`

### 9.4 Checks

#### Title

| Rule | Pass | Fail |
|---|---|---|
| Present | non-empty `<title>` | missing/empty |
| Length | 10–60 characters | outside range → warn/fail |
| Uniqueness | N/A single-page MVP | future multi-page |

Severity: missing → `high`; length → `medium`.

#### Meta Description

| Rule | Pass |
|---|---|
| Present | non-empty |
| Length | 50–160 characters |

Missing → `high`, confidence `100`.

#### Canonical

| Rule | Detail |
|---|---|
| Present | `<link rel="canonical">` exists |
| Absolute URL | Prefer absolute |
| Self-reference | Points to final URL (or allowed equivalent) |

#### Robots

| Signal | Interpretation |
|---|---|
| `noindex` in meta robots | Fail `critical` for marketing sites intent |
| robots.txt `Disallow: /` for all | Warn `high` |
| Missing robots.txt | Info / low |

#### Sitemap

| Signal | Detail |
|---|---|
| Declared or `/sitemap.xml` present | Pass |
| Absent | Fail `medium` |

#### Open Graph

Require `og:title`, `og:description`, `og:image` — each missing → `low`/`medium`.

#### Twitter Cards

Require `twitter:card`, `twitter:title` — missing → `low`.

#### Schema

| Rule | Detail |
|---|---|
| JSON-LD present | Pass info |
| JSON parseable | Fail `medium` if script present but invalid JSON |
| `@type` present | Warn if missing |

#### ALT Tags

```
alt_coverage = images_with_non_empty_alt / images_total
```

| Coverage | Status |
|---|---|
| 100% | Pass |
| 50–99% | Warn `medium` |
| < 50% or any missing on content images | Fail `high` |

#### Heading Hierarchy

| Rule | Severity |
|---|---|
| Exactly one `h1` | Fail `high` if 0 or >1 |
| Levels don't skip (h1→h3) | Warn `medium` |

#### Broken Links

For up to N internal links: issue `HEAD`/`GET` with SSRF checks.

| Result | Finding |
|---|---|
| 4xx/5xx | Fail `high`, confidence 100 |
| Timeout | Warn `medium`, confidence 70 |

#### Duplicate Metadata

MVP single-page: if title == meta description → warn `low`. Multi-page duplicates → future.

#### Internal / External Links

Emit stats findings:

- Zero internal links on non-homepage patterns → info
- All links `nofollow` → warn

### 9.5 Scoring Logic (Engine-Local)

SEO Engine does **not** compute the global Website Health Score. It emits findings; Health Score Engine applies penalties.

Optional local `seo_raw_score` may be attached for debugging:

```
seo_raw_score = max(0, 100 - Σ penalty(severity))
```

| Severity | Penalty |
|---|---|
| critical | 20 |
| high | 12 |
| medium | 6 |
| low | 2 |
| info | 0 |

### 9.6 Penalty Rules

- Only `status: fail` findings contribute penalties by default.
- `warn` may contribute half-penalty if config `penalize_warnings: true` (default false).
- Confidence < 80 → Health Score may down-weight (Part 2).

### 9.7 Future Keyword Analysis

Parked:

- Primary keyword detection from title/h1
- TF density heuristics
- SERP intent classification

Not MVP.

### 9.8 JSON Contracts

**Finding example — missing meta description:**

```json
{
  "id": "seo.meta_description.missing",
  "category": "seo",
  "check": "meta_description",
  "status": "fail",
  "severity": "high",
  "confidence": 100,
  "title": "Missing Meta Description",
  "technical_detail": "No <meta name='description'> tag found in <head>.",
  "evidence": {
    "observed": null,
    "expected": "50-160 character meta description"
  }
}
```

**Output envelope:**

```json
{
  "engine": "seo_intelligence",
  "schema_version": "engine.seo.output.v1",
  "status": "success",
  "data": {
    "findings": [],
    "metrics": {
      "title_length": 14,
      "meta_description_length": 0,
      "h1_count": 1,
      "alt_coverage": 1.0,
      "broken_links_checked": 10,
      "broken_links_failed": 0
    },
    "debug_score": 88
  }
}
```

### 9.9 Mermaid Workflow

```mermaid
flowchart TD
    A[Load parsed + crawl] --> B[Run metadata checks]
    B --> C[Run structural checks]
    C --> D{Broken link checks enabled?}
    D -- Yes --> E[Sample internal links + SSRF GET/HEAD]
    D -- No --> F[Skip with status skip]
    E --> G[Aggregate findings]
    F --> G
    G --> H[Compute metrics + debug_score]
    H --> I[Validate output schema]
    I --> J[Return SEO output]
```

### 9.10 Dependencies / Error Handling / Caching

| Topic | Rule |
|---|---|
| Dependencies | Parser + Crawler outputs; httpx for broken links |
| Hard-fail | Missing parsed input |
| Soft-fail | Broken-link subnet timeouts → partial |
| Caching | Cache broken-link results per URL for 24h |

### 9.11 Logging / Security / Performance / Testing

| Topic | Rule |
|---|---|
| Logging | Finding counts by severity; broken link sample size |
| Security | SSRF on every link check |
| Performance | Cap link checks; parallelize with semaphore (max 5) |
| Testing | Golden HTML fixtures per check; property: every fail has evidence |

### 9.12 Future Improvements

- Multi-page duplicate title/description detection
- Hreflang validation
- Crawl budget hints
- Keyword / intent analysis

---

## 10. Engine 5 — Performance Engine

### 10.1 Purpose

Measure loading performance and Core Web Vitals for the target URL using **Google PageSpeed Insights API** and/or **Lighthouse via Playwright**, then normalize results into typed performance findings and metrics.

### 10.2 Responsibilities

| In Scope | Out of Scope |
|---|---|
| Lab metrics collection | Code fixes |
| Field data when PSI provides it | Synthetic multi-geo grids (future) |
| Threshold classification (good / NI / poor) | Business ROI narrative |
| Soft-fail degradation | Blocking entire pipeline on PSI outage |

### 10.3 Inputs

| Field | Type | Required |
|---|---|---|
| `validated_url.canonical_url` | string | yes |
| `options.strategy` | `mobile` \| `desktop` | no (default `mobile`) |
| `options.providers` | `["psi","lighthouse"]` | no |
| `options.use_cache` | bool | no (default true) |

**Schema:** `engine.performance.input.v1`

### 10.4 Google PageSpeed Insights API

| Item | Detail |
|---|---|
| Endpoint | PSI v5 `pagespeedonline.googleapis.com` |
| Auth | API key via env `PAGESPEED_API_KEY` |
| Strategy | Mobile primary for MVP |
| Categories | Performance (others optional) |
| Timeout | 25s |
| On failure | Fall back to local Lighthouse |

### 10.5 Google Lighthouse (Playwright)

| Item | Detail |
|---|---|
| Runner | Playwright Chromium + Lighthouse programmatic runner |
| Form factor | Mobile emulation matching PSI where possible |
| Throttling | Lighthouse default mobile throttling |
| Timeout | 30s hard |
| Isolation | One browser context per job |

### 10.6 Metrics

| Metric | Good | Needs Improvement | Poor |
|---|---|---|---|
| **FCP** | ≤ 1.8s | 1.8–3s | > 3s |
| **LCP** | ≤ 2.5s | 2.5–4s | > 4s |
| **CLS** | ≤ 0.1 | 0.1–0.25 | > 0.25 |
| **TTFB** | ≤ 0.8s | 0.8–1.8s | > 1.8s |
| **Speed Index** | ≤ 3.4s | 3.4–5.8s | > 5.8s |
| **TBT** | ≤ 200ms | 200–600ms | > 600ms |
| **Performance Score** | ≥ 90 | 50–89 | < 50 |

Each poor/NI metric emits a finding with confidence:

- Lab metric from Lighthouse/PSI → confidence `95`–`100`
- Field-only metric with small sample → confidence `70`–`85`

### 10.7 Caching

| Key | `perf:v1:{strategy}:{canonical_url_hash}` |
|---|---|
| TTL | 24h |
| Store | Normalized metrics + provider raw reference IDs (not megabyte traces) |

### 10.8 API Limits

| Provider | Handling |
|---|---|
| PSI quota | Shared token bucket; on 429 soft-fail to Lighthouse |
| Concurrent Lighthouse | Worker concurrency cap (e.g., 2 browsers per node) |

### 10.9 Fallback Strategy

```mermaid
flowchart TD
    A[Start Performance Engine] --> B{PSI enabled & quota OK?}
    B -- Yes --> C[Call PSI]
    C --> D{PSI success?}
    D -- Yes --> E[Normalize PSI metrics]
    D -- No --> F[Fall back Lighthouse]
    B -- No --> F
    F --> G{Lighthouse success?}
    G -- Yes --> H[Normalize Lighthouse metrics]
    G -- No --> I[Return status=failed soft]
    E --> J[Emit findings]
    H --> J
```

> [!WARNING]
> Soft-fail means the pipeline continues with `performance` category marked unavailable or scored via fallback defaults **only if** config explicitly allows `allow_missing_performance`. Default MVP: mark category `partial`, set score to null, exclude from overall weighted average with renormalization (Health Score Part 2).

### 10.10 Output JSON

```json
{
  "engine": "performance",
  "schema_version": "engine.performance.output.v1",
  "status": "success",
  "data": {
    "provider": "psi+lighthouse",
    "strategy": "mobile",
    "metrics": {
      "fcp_ms": 2100,
      "lcp_ms": 4300,
      "cls": 0.12,
      "ttfb_ms": 900,
      "speed_index_ms": 4100,
      "tbt_ms": 350,
      "performance_score": 48
    },
    "classifications": {
      "lcp": "poor",
      "cls": "needs_improvement",
      "fcp": "needs_improvement"
    },
    "findings": [
      {
        "id": "perf.lcp.poor",
        "category": "performance",
        "check": "lcp",
        "status": "fail",
        "severity": "critical",
        "confidence": 98,
        "title": "Largest Contentful Paint is poor",
        "technical_detail": "LCP measured at 4300ms (poor > 4000ms).",
        "evidence": { "observed_ms": 4300, "threshold_poor_ms": 4000 }
      }
    ]
  }
}
```

### 10.11 Sequence Diagram

```mermaid
sequenceDiagram
    participant Orch as Orchestrator
    participant Perf as Performance Engine
    participant PSI as PageSpeed Insights
    participant LH as Lighthouse/Playwright
    participant Cache as Cache

    Orch->>Perf: run(url, mobile)
    Perf->>Cache: lookup
    alt hit
        Cache-->>Perf: metrics
    else miss
        Perf->>PSI: analyze(url)
        alt PSI OK
            PSI-->>Perf: lab+field
        else PSI fail
            Perf->>LH: run audit
            LH-->>Perf: lab metrics
        end
        Perf->>Cache: store
    end
    Perf-->>Orch: performance output
```

### 10.12 Validation / Errors / Logging / Security / Testing

| Area | Rule |
|---|---|
| Validation | URL must be https/http public; strategy enum |
| Errors | `PSI_UNAVAILABLE`, `LIGHTHOUSE_TIMEOUT`, `BROWSER_CRASH` — soft |
| Logging | provider used, score, LCP/CLS, cache_hit, duration |
| Security | No custom JS execution on target beyond Lighthouse; sandbox browser |
| Performance | Strict browser pool; never unbounded Chromium spawn |
| Testing | Recorded PSI fixtures; offline Lighthouse HTML harness where possible |

### 10.13 Future Improvements

- Multi-region field data
- CrUX history charts
- Element-level LTS attribution packing for AI
- Desktop + mobile dual strategy in one report

---

## 11. Engine 6 — Security Engine

### 11.1 Purpose

Assess transport security and baseline HTTP security posture for the crawled page, emitting severity-ranked findings and remediation-oriented technical details.

### 11.2 Responsibilities

| In Scope | Out of Scope |
|---|---|
| HTTPS usage | Full vulnerability scanning (XSS/SQLi) |
| TLS validity summary | Port scanning |
| Mixed content detection from HTML | WAF / bot management |
| Security headers presence/basic quality | Cookie SameSite deep audits (future) |
| Clickjacking header signals | Penetration testing |

### 11.3 Inputs

| Field | Source |
|---|---|
| `crawl.headers` | Crawler |
| `crawl.tls` | Crawler |
| `crawl.final_url` | Crawler |
| `parsed` | HTML Parser (asset URLs for mixed content) |

**Schema:** `engine.security.input.v1`

### 11.4 Checks

#### HTTPS

| Condition | Severity |
|---|---|
| Final URL is `https` | Pass |
| Final URL is `http` | `critical` |

#### SSL / TLS

| Condition | Severity |
|---|---|
| Cert valid, not expired, host matches | Pass |
| Expired / host mismatch | `critical` |
| Missing TLS metadata on HTTPS | `high` (confidence 80) |

#### Mixed Content

Scan image/script/iframe/link URLs:

| Condition | Severity |
|---|---|
| HTTPS page loads `http://` active content (script/iframe) | `critical` |
| HTTPS page loads `http://` passive content (img) | `high` |

#### Security Headers

| Header | Expectation | Missing Severity |
|---|---|---|
| `Strict-Transport-Security` | Present with reasonable `max-age` (≥ 15552000) | `high` |
| `Content-Security-Policy` | Present (basic validity) | `medium` |
| `X-Frame-Options` or CSP `frame-ancestors` | Present | `high` |
| `X-Content-Type-Options` | `nosniff` | `medium` |
| `Referrer-Policy` | Present | `low` |
| `Permissions-Policy` | Present | `low` |

#### CSP

Basic validity:

- Not empty
- Not obviously broken (`undefined` tokens)
- Warn if `unsafe-inline` + `unsafe-eval` both present → `medium`

#### HSTS

Parse `max-age`; if `< 15552000` → warn `medium`.

#### X-Frame-Options / Clickjacking

| Value | Result |
|---|---|
| `DENY` / `SAMEORIGIN` | Pass |
| Missing and no CSP frame-ancestors | Fail `high` |
| `ALLOW-FROM` | Warn deprecated |

### 11.5 Recommendations (Technical)

Each finding includes `technical_detail` describing the fix (e.g., “Add `Strict-Transport-Security: max-age=31536000; includeSubDomains`”). Business language is **not** authored here — Business Impact / AI engines own that.

### 11.6 Severity Levels

| Level | Examples |
|---|---|
| critical | HTTP-only site, invalid TLS, active mixed content |
| high | Missing HSTS, missing frame protection |
| medium | Weak CSP, missing nosniff |
| low | Missing Referrer-Policy |
| info | Informational header observations |

### 11.7 Output JSON

```json
{
  "engine": "security",
  "schema_version": "engine.security.output.v1",
  "status": "success",
  "data": {
    "https": true,
    "tls": { "valid": true, "expires_at": "2027-01-01T00:00:00Z" },
    "headers_observed": ["strict-transport-security", "x-content-type-options"],
    "findings": [
      {
        "id": "sec.hsts.missing",
        "category": "security",
        "check": "hsts",
        "status": "fail",
        "severity": "high",
        "confidence": 100,
        "title": "Missing Strict-Transport-Security header",
        "technical_detail": "No HSTS header was returned on the final response.",
        "evidence": { "header": "strict-transport-security", "observed": null }
      }
    ]
  }
}
```

### 11.8 Workflow Diagram

```mermaid
flowchart TD
    A[Read crawl + parsed] --> B[Check HTTPS scheme]
    B --> C[Validate TLS summary]
    C --> D[Scan assets for mixed content]
    D --> E[Evaluate security headers]
    E --> F[Evaluate CSP / HSTS / framing]
    F --> G[Emit findings + evidence]
    G --> H[Schema validate output]
```

### 11.9 Algorithms / Validation / Failure / Caching

| Topic | Rule |
|---|---|
| Mixed content | Parse absolute URLs vs page scheme |
| Validation | Requires crawl headers object |
| Failure | Hard-fail only if crawl missing; else success with findings |
| Caching | Derived from crawl hash; no independent network |

### 11.10 Logging / Security / Performance / Testing / Future

| Topic | Rule |
|---|---|
| Logging | Finding counts; https boolean; header presence map |
| Security | Do not treat header presence as full guarantee; confidence honest |
| Performance | Pure CPU on artifacts; < 100ms typical |
| Testing | Header matrix fixtures; mixed content HTML fixtures |
| Future | Cookie flags, CAA records, CT logs, advanced CSP analysis |

---

## 12. Engine 7 — Accessibility Engine

### 12.1 Purpose

Evaluate baseline accessibility signals against **WCAG-oriented** rules using the parsed DOM (and optional lab signals), emitting findings with confidence that distinguishes deterministic issues from heuristic ones.

### 12.2 Responsibilities

| In Scope | Out of Scope |
|---|---|
| Heading structure | Full manual a11y audit |
| Image ALT presence | Screen-reader UX certification |
| Form labels | Automated keyboard traversal of all widgets (MVP best-effort) |
| ARIA validity basics | Legal compliance attestation |
| Contrast heuristics (static) | Guaranteeing AA/AAA |

### 12.3 Inputs

| Field | Source |
|---|---|
| `parsed` | HTML Parser |
| `options.run_contrast_heuristic` | bool default true |
| `options.locale` | string default `en` |

**Schema:** `engine.accessibility.input.v1`

### 12.4 Checks

#### ARIA

| Check | Confidence | Severity |
|---|---|---|
| Invalid ARIA role | 90 | high |
| `aria-*` on unsupported roles | 80 | medium |
| Conflicting ARIA / native semantics | 75 | medium |

#### Labels

| Check | Confidence |
|---|---|
| Input without label / name | 100 |
| Button without accessible name | 95 |

#### Contrast

Static heuristic on inline styles / paired theme tokens when available:

| Result | Confidence |
|---|---|
| Deterministic pair fails WCAG AA 4.5:1 | 90 |
| Suspected failure without computed styles | **74** |
| Skip when colors unknown | `status: skip` |

> [!NOTE]
> Heuristic contrast findings **must** use titles like “Potential Accessibility Issue” and confidence < 90 so UI does not over-claim.

#### Keyboard Navigation

Best-effort static checks:

- Elements with `onclick` but non-focusable → warn confidence 70
- Positive `tabindex` > 0 → warn confidence 85

#### Heading Structure

Reuse parser heading list; align with SEO but categorize as `accessibility` with WCAG `1.3.1` reference.

#### Screen Readers

Checks that improve SR experience:

- `html[lang]` missing → medium, confidence 100
- `img` empty alt on likely informative images → high, confidence 85

### 12.5 Accessibility Score (Engine-Local Debug)

Same penalty table as SEO debug score; Health Score Engine owns official score.

### 12.6 WCAG References

| Check | WCAG |
|---|---|
| Heading hierarchy | 1.3.1 |
| Color contrast | 1.4.3 (AA) |
| Form labels | 1.3.1 / 4.1.2 |
| Image ALT | 1.1.1 |
| ARIA validity | 4.1.2 |
| Language of page | 3.1.1 |

### 12.7 Recommendations

Technical remediation strings only, e.g.:

- “Associate `<label for>` with each input `id`.”
- “Provide non-empty `alt` for informative images; use `alt=\"\"` for decorative.”

### 12.8 Output JSON

```json
{
  "engine": "accessibility",
  "schema_version": "engine.accessibility.output.v1",
  "status": "success",
  "data": {
    "metrics": {
      "inputs_missing_labels": 2,
      "images_missing_alt": 1,
      "lang_present": true
    },
    "findings": [
      {
        "id": "a11y.contrast.potential_aa_fail",
        "category": "accessibility",
        "check": "contrast",
        "status": "fail",
        "severity": "medium",
        "confidence": 74,
        "title": "Potential Accessibility Issue",
        "technical_detail": "Heuristic contrast analysis flagged possible AA failure on secondary text.",
        "wcag": "1.4.3",
        "evidence": {
          "foreground": "#8899aa",
          "background": "#ffffff",
          "ratio_estimated": 2.8
        }
      }
    ]
  }
}
```

### 12.9 Mermaid Diagram

```mermaid
flowchart TD
    A[Parsed Document] --> B[Lang + landmarks basics]
    A --> C[Headings structure]
    A --> D[Images ALT]
    A --> E[Forms labels]
    A --> F[ARIA validation]
    A --> G{Contrast heuristic enabled?}
    G -- Yes --> H[Estimate contrast pairs]
    G -- No --> I[Skip contrast]
    B --> J[Collect findings]
    C --> J
    D --> J
    E --> J
    F --> J
    H --> J
    I --> J
    J --> K[Attach WCAG refs + confidence]
    K --> L[Emit accessibility output]
```

### 12.10 Validation / Failure / Caching / Logging

| Topic | Rule |
|---|---|
| Validation | Requires parser stats + forms/images arrays |
| Failure | Hard-fail only on missing parser output |
| Caching | Derived from parsed content hash |
| Logging | counts by check; contrast heuristic enabled flag |

### 12.11 Security / Performance / Testing / Future

| Topic | Rule |
|---|---|
| Security | No fetching of external CSS in MVP contrast path (prevents SSRF); inline only |
| Performance | Cap contrast pairs evaluated (e.g., 200) |
| Testing | Fixtures for missing labels, bad roles, contrast suspects |
| Future | axe-core integration, computed style via browser, full keyboard crawler |

---

---

## 13. Part 2 — Intelligence, Assembly & Platform

**Part 1** (Engines 1–7) produces **technical truth**: validated URLs, crawl artifacts, parsed documents, and category findings.

**Part 2** (Engines 8–14) turns that truth into **scored, business-framed, quality-gated, AI-explained, customer-facing artifacts** — without inventing facts Part 1 did not observe.

| Layer | Engines | Role |
|---|---|---|
| Scoring | Health Score | Aggregate findings → category + overall scores |
| Business translation | Business Impact, ROI | Map technical findings → impact, effort, value |
| Quality gate | Data Quality | Normalize, validate, and sanitize before AI |
| Explanation | AI Recommendation | Explain and recommend — never invent checks |
| Assembly | Report Builder, PDF | Single source of truth → dashboard + export |

> [!NOTE]
> Engine numbering continues from Part 1. Shared standards in §4 still apply to every Part 2 engine.

---

## 14. Engine 8 — Health Score Engine

### 14.1 Purpose

Aggregate findings from SEO, Performance, Security, and Accessibility (plus best-practices signals) into **category scores (0–100)** and a single **Website Health Score (0–100)** using configurable weights and severity penalties.

This engine answers: *How healthy is this website, numerically, in a way we can defend and version?*

### 14.2 Responsibilities

| In Scope | Out of Scope |
|---|---|
| Weighted category aggregation | Inventing findings |
| Severity → penalty application | Business narrative copy |
| Renormalization when a category is missing | AI prompting |
| Config version stamping | PDF / dashboard rendering |

### 14.3 Inputs

| Field | Source | Required |
|---|---|---|
| `seo` | SEO Intelligence output | yes (may be empty findings) |
| `performance` | Performance output | soft — may be `partial` / missing |
| `security` | Security output | yes |
| `accessibility` | Accessibility output | yes |
| `best_practices_findings` | Optional Lighthouse BP findings | no |
| `scoring_config` | `scoring_config.json` snapshot | yes |

**Schema:** `engine.health_score.input.v1`

### 14.4 Weighted Scoring

| Category | Default Weight |
|---|---|
| SEO | 25% |
| Performance | 30% |
| Security | 20% |
| Accessibility | 15% |
| Best Practices | 10% |

Weights **must** sum to `1.0` (± 0.001). Invalid configs fail closed with `INVALID_SCORING_CONFIG`.

### 14.5 Penalty System

Each category starts at **100**.

| Severity | Default Penalty |
|---|---|
| `critical` | −20 |
| `high` | −12 |
| `medium` | −6 |
| `low` | −2 |
| `info` | 0 |

**Rules:**

- Only findings with `status: fail` apply full penalties by default.
- `status: warn` applies `warn_penalty_factor` (default `0.0`; may be set to `0.5` in config).
- Findings with `confidence < confidence_penalty_floor` (default `80`) apply `penalty * (confidence / 100)`.
- Category score floors at `0`.

### 14.6 Normalization

When a category is unavailable (e.g., Performance soft-failed):

```
available_weight_sum = Σ weight(c) for c in present_categories
overall = Σ (weight(c) / available_weight_sum) * score(c)
```

Stamp `meta.renormalized: true` and list excluded categories.

> [!WARNING]
> Do **not** silently substitute `score=100` for missing categories. That inflates health and destroys trust.

### 14.7 Configuration

`scoring_config.json` (versioned):

```json
{
  "version": "scoring_config@3",
  "weights": {
    "seo": 0.25,
    "performance": 0.30,
    "security": 0.20,
    "accessibility": 0.15,
    "best_practices": 0.10
  },
  "penalties": {
    "critical": 20,
    "high": 12,
    "medium": 6,
    "low": 2,
    "info": 0
  },
  "warn_penalty_factor": 0.0,
  "confidence_penalty_floor": 80,
  "allow_missing_performance": true
}
```

### 14.8 Formula

```
category_score(c) = max(0, 100 - Σ effective_penalty(f) for f in findings(c))

effective_penalty(f) =
  base_penalty(f.severity)
  * (warn_penalty_factor if f.status == warn else 1.0 if f.status == fail else 0.0)
  * (f.confidence / 100 if f.confidence < confidence_penalty_floor else 1.0)

overall_score = round(Σ weight'(c) * category_score(c))
```

where `weight'(c)` is the renormalized weight if needed.

### 14.9 Examples

**Example A — all categories present**

| Category | Penalties | Score |
|---|---|---|
| SEO | high (−12) + medium (−6) | 82 |
| Performance | critical (−20) + high (−12) | 68 |
| Security | medium (−6) | 94 |
| Accessibility | high (−12) + low (−2) | 86 |
| Best Practices | low (−2) | 98 |

```
overall = 0.25(82)+0.30(68)+0.20(94)+0.15(86)+0.10(98)
        = 20.5 + 20.4 + 18.8 + 12.9 + 9.8
        = 82.4 → 82
```

**Example B — confidence-weighted penalty**

Accessibility finding: `severity=high` (−12), `confidence=74` (< 80):

```
effective = 12 * (74/100) = 8.88
```

**Example C — missing Performance**

Present weights: 0.25+0.20+0.15+0.10 = 0.70  
SEO weight' = 0.25/0.70 ≈ 0.357, etc. `renormalized: true`.

### 14.10 Configurable Weights

| Surface | Capability |
|---|---|
| MVP | Global `scoring_config.json` |
| Enterprise (future) | Per-tenant weight overrides |
| Runtime | Config hash embedded in every report for auditability |

### 14.11 Output JSON

```json
{
  "engine": "health_score",
  "schema_version": "engine.health_score.output.v1",
  "status": "success",
  "data": {
    "scores": {
      "overall": 82,
      "seo": 82,
      "performance": 68,
      "security": 94,
      "accessibility": 86,
      "best_practices": 98
    },
    "penalties_applied": {
      "seo": 18,
      "performance": 32,
      "security": 6,
      "accessibility": 14,
      "best_practices": 2
    },
    "meta": {
      "config_version": "scoring_config@3",
      "renormalized": false,
      "excluded_categories": []
    }
  }
}
```

### 14.12 Future ML-based Scoring

Parked (not MVP):

- Learn weights from agency “accepted priority” feedback
- Segment-aware models (e-commerce vs brochure)
- Calibrate penalties against real conversion outcomes
- Always keep a **deterministic fallback scorer** — ML must never be the only path

### 14.13 Failure Handling / Testing

| Topic | Rule |
|---|---|
| Invalid config | Hard-fail `INVALID_SCORING_CONFIG` |
| No findings at all | Scores = 100 with warning `NO_FINDINGS` |
| Testing | Golden matrices for penalties, renormalization, confidence scaling |

---

## 15. Engine 9 — Business Impact Engine

### 15.1 Purpose

Map every technical finding to **business language**: impact category, expected outcome, difficulty, estimated time, and priority — so a non-technical reader knows what matters and why.

### 15.2 Responsibilities

| In Scope | Out of Scope |
|---|---|
| Deterministic business mapping tables | Guaranteed revenue numbers |
| Priority assignment | LLM prose generation |
| Effort heuristics by `check_id` | PDF layout |
| Passing through confidence | Inventing new issues |

### 15.3 Inputs

| Field | Source |
|---|---|
| `findings[]` | Union of SEO / Perf / Security / A11y findings |
| `scores` | Health Score output (optional context) |
| `mapping_config` | `business_mapping.json` |

**Schema:** `engine.business_impact.input.v1`

### 15.4 Business Mapping

Each `check_id` maps to a template:

| Field | Example |
|---|---|
| `business_impact` | Lower CTR from Search |
| `impact_domain` | `seo` \| `revenue` \| `conversion` \| `brand_trust` \| `compliance` |
| `expected_outcome` | Improved snippet quality in search results |
| `default_difficulty` | Easy |
| `default_time_range` | 5–15 minutes |
| `business_impact_weight` | 0.0–1.0 |

Unknown `check_id` → generic template + warning `UNMAPPED_CHECK`; never drop the finding.

### 15.5 Revenue Impact

| Finding class | Business framing (hedged) |
|---|---|
| Poor LCP / high TBT | Likely lost conversions from slow mobile experiences |
| Checkout-impacting a11y (future) | Friction that can reduce completed purchases |
| Downtime / TLS failure | Direct trust and transaction risk |

MVP emits qualitative `impact_domain: revenue` — **no fabricated $ amounts**.

### 15.6 SEO Impact

| Finding class | Framing |
|---|---|
| Missing meta / title | Lower CTR from Search |
| `noindex` / robots blocks | Pages may not appear in search |
| Broken internal links | Wasted crawl equity / poor discovery |
| Missing sitemap | Slower discovery of URLs |

### 15.7 Conversion Impact

| Finding class | Framing |
|---|---|
| Performance poor thresholds | Higher bounce risk before content paints |
| Form labels missing | Friction and errors in lead forms |
| Mixed content warnings | Browser interventions that interrupt journeys |

### 15.8 Brand Trust Impact

| Finding class | Framing |
|---|---|
| HTTP-only / invalid TLS | Browser warnings damage credibility |
| Missing HSTS / weak headers | Weaker security posture signal |
| Accessibility gaps | Exclusion risk; brand/compliance perception |

### 15.9 Priority Assignment

```
priority_score = severity_weight[severity] * business_impact_weight[check_id] * confidence_factor
```

| Severity | `severity_weight` |
|---|---|
| critical | 1.00 |
| high | 0.75 |
| medium | 0.50 |
| low | 0.25 |
| info | 0.10 |

| `priority_score` | Priority |
|---|---|
| ≥ 0.80 | Critical |
| ≥ 0.55 | High |
| ≥ 0.30 | Medium |
| < 0.30 | Low |

`confidence_factor = confidence / 100` (heuristic issues naturally rank lower).

### 15.10 Decision Tree

```mermaid
flowchart TD
    A[Finding] --> B{Mapped check_id?}
    B -- No --> C[Apply generic template + UNMAPPED_CHECK]
    B -- Yes --> D[Load business template]
    C --> E[Compute priority_score]
    D --> E
    E --> F{priority_score thresholds}
    F --> G[Critical / High / Medium / Low]
    G --> H[Attach difficulty + time range]
    H --> I[Emit business impact object]
```

### 15.11 Examples

**Missing Meta Description**

| Field | Value |
|---|---|
| Business Impact | Lower CTR from Search |
| Impact Domain | seo |
| Expected Outcome | Improved snippet quality in search results |
| Difficulty | Easy |
| Est. Time | 5 minutes |
| Priority | High |
| Confidence | 100% |

**Potential Accessibility Issue (contrast heuristic)**

| Field | Value |
|---|---|
| Business Impact | Risk of excluding users / WCAG gap |
| Impact Domain | compliance |
| Priority | Medium (confidence 74% dampens score) |
| Confidence | 74% |

### 15.12 JSON Contracts

```json
{
  "engine": "business_impact",
  "schema_version": "engine.business_impact.output.v1",
  "status": "success",
  "data": {
    "issues": [
      {
        "finding_id": "seo.meta_description.missing",
        "issue": "Missing Meta Description",
        "business_impact": "Lower CTR from Search",
        "impact_domain": "seo",
        "expected_outcome": "Improved snippet quality in search results",
        "difficulty": "Easy",
        "estimated_time": "5 minutes",
        "priority": "High",
        "confidence": 100,
        "severity": "high",
        "category": "seo",
        "technical_detail": "No <meta name='description'> tag found in <head>."
      }
    ]
  }
}
```

### 15.13 Testing / Future

- Golden mapping coverage: every MVP `check_id` must have a template (CI check).
- Future: industry-specific mapping packs; localization of business copy.

---

## 16. Engine 10 — ROI Engine

### 16.1 Purpose

Enrich each business-impact issue with **estimated development time**, **difficulty**, **estimated cost bands**, **business value** (hedged), and an **ROI-oriented priority signal** — without promising numerical returns.

### 16.2 Responsibilities

| In Scope | Out of Scope |
|---|---|
| Effort/cost band estimation | Guaranteed traffic/revenue lifts |
| Value category tagging | Invoice generation |
| ROI score for sorting | Changing technical findings |
| Confidence pass-through / dampening | LLM storytelling (AI Engine) |

### 16.3 Inputs

| Field | Source |
|---|---|
| `issues[]` | Business Impact output |
| `cost_config` | Hourly rate bands, difficulty multipliers |
| `scores` | Health Score (context) |

**Schema:** `engine.roi.input.v1`

### 16.4 Estimated Development Time

Inherited from Business Impact templates; ROI Engine may refine ranges:

| Difficulty | Default Time Range |
|---|---|
| Easy | 5 min – 1 hr |
| Medium | 1 hr – 1 day |
| Hard | 1 day+ |

Normalize to hours for aggregation:

```
estimated_hours_mid = midpoint(time_range)
total_effort_hours = Σ estimated_hours_mid
```

Display as a range, e.g. `"14–22 hours"`.

### 16.5 Difficulty

`Easy` | `Medium` | `Hard` — never invented by AI; sourced from mapping tables.

### 16.6 Estimated Cost

MVP uses configurable hourly rates (not user-facing currency promises without disclaimer):

```
cost_low  = hours_low  * hourly_rate_low
cost_high = hours_high * hourly_rate_high
```

Default illustrative rates in config (e.g., $75–$150/hr). Label as **indicative**.

### 16.7 Business Value

Approved value categories only (align with PRD §9.11):

- Faster website
- Better user experience
- Potential SEO improvements
- Improved crawlability
- Reduced bounce rate
- Improved trust / security posture
- Improved accessibility / inclusion

> [!WARNING]
> **Never** emit guaranteed outcomes or fabricated percentage lifts (`+34% traffic`). Use hedged language only.

### 16.8 Confidence

```
roi_confidence = min(issue.confidence, mapping_confidence_default)
```

Heuristic issues keep lower confidence; cost/value language must reflect uncertainty when `< 90`.

### 16.9 Priority

ROI Engine may produce `roi_priority` for sorting:

```
roi_priority_score = business_value_weight * (1 / effort_hours_mid) * (confidence/100)
```

Does not override Security-critical issues: if `severity == critical`, clamp display priority to at least `High`.

### 16.10 ROI Calculation

Conceptual ROI signal (unitless, for ranking — not finance accounting):

```
roi_index = (business_value_weight * impact_severity_factor) / max(effort_hours_mid, 0.1)
```

| Band | Interpretation |
|---|---|
| High `roi_index` | Quick wins |
| Low `roi_index` | Strategic / expensive fixes |

### 16.11 Examples

| Issue | Effort | Cost band (indicative) | Value | ROI signal |
|---|---|---|---|---|
| Missing Meta Description | 5–15 min | $10–$40 | Potential SEO improvements | Quick win |
| LCP > 4s | 3–5 hrs | $225–$750 | Reduced bounce rate | High value / medium effort |
| CSP hardening | 4–8 hrs | $300–$1,200 | Improved trust / security posture | Strategic |

### 16.12 Output JSON

```json
{
  "engine": "roi",
  "schema_version": "engine.roi.output.v1",
  "status": "success",
  "data": {
    "issues": [
      {
        "finding_id": "seo.meta_description.missing",
        "difficulty": "Easy",
        "estimated_time": "5 minutes",
        "estimated_hours": { "low": 0.08, "high": 0.25 },
        "estimated_cost_usd": { "low": 6, "high": 40, "indicative": true },
        "business_value": "Potential SEO improvements",
        "value_categories": ["Potential SEO improvements"],
        "confidence": 100,
        "priority": "High",
        "roi_index": 9.4,
        "roi_band": "quick_win"
      }
    ],
    "totals": {
      "estimated_total_effort": "14-22 hours",
      "estimated_total_cost_usd": { "low": 1050, "high": 3300, "indicative": true }
    }
  }
}
```

---

## 17. Engine 11 — Data Quality Engine

### 17.1 Purpose

Validate, normalize, deduplicate, and completeness-check the enriched issue set **before** any LLM call. This is the quality gate that keeps AI honest and prompts cheap.

### 17.2 Why AI Must Never Receive Raw Engine Outputs

| Risk | What goes wrong |
|---|---|
| Token explosion | Raw HTML, header dumps, and duplicate findings blow budgets |
| Hallucination fuel | Ambiguous/conflicting fields invite invention |
| Schema drift | LLM sees unstable shapes → invalid JSON |
| Secret leakage | Cookies, tokens, PII in headers/scripts reach the model |
| Non-determinism | Unordered arrays change prompts → flaky outputs |
| Over-trust | Heuristic findings without confidence gates look like facts |

> [!WARNING]
> The AI Recommendation Engine’s only legal input is **Data Quality Engine output** (`engine.data_quality.output.v*`). Orchestrators that pass raw crawl/parser payloads to the LLM are architecture-violating.

### 17.3 Responsibilities

| In Scope | Out of Scope |
|---|---|
| Schema validation of upstream envelopes | Re-crawling |
| Normalization & dedupe | Business copy rewriting |
| Confidence recalibration hooks | Model calls |
| Completeness scoring | PDF generation |
| Redaction of sensitive evidence | Inventing missing findings |

### 17.4 Input Validation

Validate presence and schema versions for:

- Health Score output
- Business Impact issues
- ROI enrichment
- Source findings (for evidence cross-check)

Reject with `DQ_INPUT_INVALID` if required envelopes fail schema.

### 17.5 Output Validation

Post-conditions before success:

- Every issue has: `finding_id`, `category`, `severity`, `confidence`, `priority`, `business_impact`, `technical_detail`
- `confidence` ∈ [0, 100]
- No raw HTML fields
- Evidence size capped (e.g., ≤ 2KB per issue)

### 17.6 Data Normalization

| Rule | Behavior |
|---|---|
| Priority casing | `Critical` \| `High` \| `Medium` \| `Low` |
| Category enum | `seo` \| `performance` \| `security` \| `accessibility` \| `best_practices` |
| Sort | Critical→Low, then `roi_index` desc |
| Strings | Trim; collapse whitespace |
| IDs | Stable `finding_id` required |

### 17.7 Confidence Calculation

DQ may adjust confidence only via documented rules:

```
if evidence incomplete → confidence = min(confidence, 80)
if check marked heuristic → confidence = min(confidence, 85)
if conflicting findings resolved by drop → survivor keeps confidence
```

Never **raise** confidence above upstream without new evidence.

### 17.8 Conflict Detection

| Conflict | Resolution |
|---|---|
| Same `finding_id` twice | Keep higher severity; merge evidence |
| Pass + fail same check | Prefer fail; warn `CONFLICT_PASS_FAIL` |
| SEO vs A11y duplicate heading issues | Keep both categories but link `related_ids` |

### 17.9 Missing Data Detection

| Missing | Action |
|---|---|
| No scores.overall | Fail DQ |
| Category empty with engine `failed` | Mark `gaps[]` |
| Issue missing business fields | Fail or drop with `INCOMPLETE_ISSUE` |

### 17.10 Report Completeness

```
completeness = required_sections_present / required_sections_total
```

Required sections MVP: `scores`, `issues`, `overview_ready` (URL/title), `categories_covered`.

`completeness < 0.7` → status `partial` and AI may only summarize available sections.

### 17.11 Quality Rules

| Rule ID | Description |
|---|---|
| `QR_NO_HTML` | Strip/forbid HTML bodies |
| `QR_NO_SECRETS` | Redact cookie/authorization patterns |
| `QR_MAX_ISSUES` | Cap issues sent to AI (e.g., top 40 by priority) |
| `QR_MIN_CONFIDENCE_DISPLAY` | Issues < 50 confidence flagged `low_trust` |
| `QR_STABLE_ORDER` | Deterministic sort for prompt hashing |

### 17.12 JSON Contracts

```json
{
  "engine": "data_quality",
  "schema_version": "engine.data_quality.output.v1",
  "status": "success",
  "data": {
    "completeness": 0.95,
    "gaps": [],
    "warnings": [],
    "scores": { "overall": 82, "seo": 82, "performance": 68, "security": 94, "accessibility": 86, "best_practices": 98 },
    "issues": [],
    "ai_payload": {
      "schema_version": "ai.prompt_payload.v1",
      "url": "https://example.com/",
      "scores": {},
      "issues": [],
      "constraints": {
        "max_issues": 40,
        "forbid_invented_metrics": true,
        "language": "en"
      }
    },
    "quality": {
      "issues_in": 28,
      "issues_out": 28,
      "duplicates_removed": 0,
      "redactions": 1
    }
  }
}
```

### 17.13 Mermaid Workflow

```mermaid
flowchart TD
    A[Upstream enriched outputs] --> B[Schema validate envelopes]
    B --> C{Valid?}
    C -- No --> X[Fail DQ_INPUT_INVALID]
    C -- Yes --> D[Normalize fields + enums]
    D --> E[Detect conflicts + dedupe]
    E --> F[Redact secrets / strip HTML]
    F --> G[Recalibrate confidence rules]
    G --> H[Compute completeness]
    H --> I[Build ai_payload]
    I --> J[Validate output contract]
    J --> K[Emit DQ output]
```

---

## 18. Engine 12 — AI Recommendation Engine

### 18.1 Purpose

Transform the Data Quality `ai_payload` into **plain-language explanations and actionable recommendations** per issue, plus an executive summary — strictly grounded in provided data.

### 18.2 Responsibilities

| In Scope | Out of Scope |
|---|---|
| Prompt build + versioned templates | Creating new finding IDs |
| LLM JSON-mode calls | Guaranteed ROI percentages |
| Fallback templates | Fetching live site content |
| Response schema validation | Scoring math |

### 18.3 Prompt Builder

Pipeline:

1. Load prompt template by `prompt_version`
2. Inject `ai_payload` JSON
3. Inject hard constraints block
4. Request structured JSON output only
5. Hash prompt for cache key / audit

### 18.4 Prompt Versioning

| Field | Example |
|---|---|
| `prompt_id` | `recommendation.executive_and_issues` |
| `prompt_version` | `v4` |
| Storage | `apps/api/app/engines/recommendations/prompts/` |
| Change control | PR + golden fixture updates required |

### 18.5 OpenAI Integration

| Setting | MVP |
|---|---|
| API | Chat Completions / Responses with JSON mode |
| Model | Config `OPENAI_MODEL` |
| Temperature | `0`–`0.2` |
| Timeout | 20s |
| Max tokens | Sized to issue cap |

### 18.6 Gemini Integration

| Setting | MVP |
|---|---|
| Role | Secondary / fallback provider |
| Model | Config `GEMINI_MODEL` |
| Same JSON schema | Required |

### 18.7 Fallback Models

Order:

1. Primary (OpenAI)
2. Secondary (Gemini)
3. Rule-based template renderer (no LLM)

Rule-based fallback uses Business Impact + ROI fields only — still valid report, lower prose quality.

### 18.8 JSON Outputs

```json
{
  "engine": "ai_recommendation",
  "schema_version": "engine.ai_recommendation.output.v1",
  "status": "success",
  "data": {
    "prompt_version": "recommendation.executive_and_issues@v4",
    "provider": "openai",
    "executive_summary": "example.com scores 82/100 overall...",
    "recommendations": [
      {
        "finding_id": "seo.meta_description.missing",
        "business_explanation": "Search engines are writing their own snippet...",
        "recommended_action": "Add a unique 50-160 character meta description...",
        "estimated_effort": "Easy (5 minutes)",
        "priority": "High",
        "expected_improvement": "Improved click-through rate from search results",
        "confidence": 100
      }
    ]
  }
}
```

### 18.9 Hallucination Prevention

| Control | Rule |
|---|---|
| Closed world | May only reference `finding_id`s in payload |
| No new metrics | Cannot invent scores or % lifts |
| No new issues | Cannot add findings not in input |
| Hedged language | Must use approved value categories |
| Reject on violation | `AI_SCHEMA_VIOLATION` / `AI_INVENTED_FINDING` → fallback |

### 18.10 Confidence Scores

AI **must not inflate** confidence. Output confidence = input issue confidence (pass-through). Prose for confidence `< 90` must include uncertainty cues (“potential”, “likely”).

### 18.11 Response Validation

| Check | Action |
|---|---|
| Valid JSON | Else retry once / fallback |
| All `finding_id`s ⊆ input set | Else strip unknowns + warn |
| Required fields present | Else fallback per issue |
| Executive summary length 3–5 sentences | Trim/retry |

### 18.12 Prompt Examples

**System (excerpt):**

```text
You are SitePilot AI. Explain website audit findings for business readers.
Use ONLY the JSON payload. Do not invent issues, metrics, or guarantees.
Return JSON matching the schema. Pass through confidence unchanged.
```

**User (excerpt):**

```text
Payload:
{{ai_payload}}

Constraints:
- forbid_invented_metrics: true
- approved_value_categories: [...]
- output_schema: ai.recommendation.v1
```

### 18.13 Mermaid Flow

```mermaid
flowchart TD
    A[DQ ai_payload] --> B[Build versioned prompt]
    B --> C[Call primary LLM JSON mode]
    C --> D{Valid + grounded?}
    D -- Yes --> E[Emit recommendations]
    D -- No --> F[Retry once / secondary provider]
    F --> G{Valid?}
    G -- Yes --> E
    G -- No --> H[Rule-based fallback templates]
    H --> E
```

---

## 19. Engine 13 — Report Builder Engine

### 19.1 Purpose

Assemble the **single source-of-truth report JSON** consumed by the Frontend Dashboard and PDF Engine. No divergent data models.

### 19.2 Responsibilities

| In Scope | Out of Scope |
|---|---|
| Merge engine outputs into report schema | Live crawling |
| Executive summary attachment | Pixel PDF layout |
| Issue prioritization final order | Auth/billing |
| Chart-ready series | Client rendering |

### 19.3 Combine Engine Outputs

Merge:

- URL Validation / Crawler / Parser → `overview`
- Health Score → `scores`
- DQ + AI → `issues` + `executive_summary`
- ROI totals → `estimated_total_effort`, cost bands
- Engine run meta → `pipeline`

### 19.4 Executive Summary

Prefer AI-generated summary; if missing, synthesize rule-based summary from scores + top 3 critical/high issues.

### 19.5 Issue Prioritization

Final sort:

1. Priority (Critical→Low)
2. `roi_index` desc
3. `confidence` desc
4. `finding_id` asc (stable)

### 19.6 Business Summary

Optional block:

```json
{
  "top_opportunities": [],
  "quick_wins": [],
  "strategic_fixes": []
}
```

Derived from ROI bands.

### 19.7 Charts

Emit chart-ready data (not images):

| Chart | Series |
|---|---|
| Category gauges | `scores.*` |
| Priority breakdown | counts by priority |
| Effort by category | hours aggregated |

### 19.8 Dashboard Data

Report JSON **is** dashboard data. Frontend must not recompute scores.

### 19.9 JSON Output

Align with API `GET /report/{id}` (see PRD / API_SPEC). Required top-level keys:

`report_id`, `url`, `status`, `overview`, `scores`, `executive_summary`, `issues[]`, `estimated_total_effort`, `charts`, `pipeline`, `created_at`, `completed_at`

### 19.10 Sequence Diagram

```mermaid
sequenceDiagram
    participant Orch as Orchestrator
    participant DQ as Data Quality
    participant AI as AI Recommendations
    participant RB as Report Builder
    participant DB as PostgreSQL
    participant FE as Frontend

    Orch->>DQ: validate enriched outputs
    DQ-->>Orch: ai_payload + issues
    Orch->>AI: recommend(ai_payload)
    AI-->>Orch: executive_summary + recommendations
    Orch->>RB: assemble(all artifacts)
    RB->>RB: merge + sort + charts
    RB->>DB: persist report JSON status=complete
    FE->>DB: GET report via API
    FE-->>FE: Render Dashboard
```

---

## 20. Engine 14 — PDF Engine

### 20.1 Purpose

Render the persisted report JSON into a **professional, branded PDF** for download/share, using the same data as the dashboard.

### 20.2 Responsibilities

| In Scope | Out of Scope |
|---|---|
| ReportLab composition | Editing scores |
| Embedding chart images | HTML-to-PDF browser printing as MVP source of truth |
| Object storage upload + signed URL | White-label theming (future) |

### 20.3 Professional PDF

| Spec | MVP |
|---|---|
| Format | A4 |
| Length | 8–12 pages target |
| Sections | Cover, Executive Summary, Scores, Category breakdowns, Issues table, Recommendations, Contact CTA |
| Print | High contrast, avoid pure-black floods |

### 20.4 Charts

Server-side render chart images from `report.charts` (e.g., matplotlib / cairo) and embed. Do not screenshot the Next.js app for MVP.

### 20.5 Tables

Issues table columns: Issue, Category, Priority, Confidence, Impact, Effort.

Paginate cleanly; repeat header row.

### 20.6 Company Branding

| Element | MVP |
|---|---|
| Logo | SitePilot mark from `assets/` |
| Colors | Brand tokens from config |
| Footer | `sitepilot.ai` + report id + generated timestamp |

### 20.7 Export Strategy

```mermaid
flowchart TD
    A[Report status=complete] --> B[Enqueue PDF job]
    B --> C[Render PDF bytes]
    C --> D[Upload object storage]
    D --> E[Signed URL TTL]
    E --> F[Patch report.pdf_url]
```

| Item | Default |
|---|---|
| Trigger | On-demand `GET /report/{id}/pdf` or async after report complete |
| TTL signed URL | 24h |
| Idempotency | Content-hash of report JSON → reuse PDF |

### 20.8 Future White-label Reports

- Agency logo/colors
- Remove SitePilot footer
- Custom cover letter
- Requires Agency tier + branding config

### 20.9 Output

```json
{
  "engine": "pdf",
  "schema_version": "engine.pdf.output.v1",
  "status": "success",
  "data": {
    "pdf_url": "https://storage.sitepilot.ai/reports/rep_9f3ac21e.pdf",
    "expires_at": "2026-07-13T10:15:00Z",
    "bytes": 524288,
    "renderer": "reportlab",
    "content_hash": "sha256:..."
  }
}
```

---

## 21. Inter-Engine Communication

### 21.1 Rules

1. Engines **never** import/call sibling engines.
2. Only the **Pipeline Orchestrator** reads/writes artifacts.
3. Communication is **typed JSON contracts** stored in the artifact store (DB/object/Redis).
4. Each message includes `schema_version`, `report_id`, `trace_id`.

### 21.2 Artifact Store Keys

```
artifacts:{report_id}:{engine}:{schema_version}
```

### 21.3 Orchestration Sequence (Full)

```mermaid
sequenceDiagram
    participant API as API
    participant Orch as Orchestrator
    participant V as URL Validation
    participant C as Crawler
    participant P as Parser
    participant SEO as SEO
    participant PERF as Performance
    participant SEC as Security
    participant A11Y as Accessibility
    participant HS as Health Score
    participant BI as Business Impact
    participant ROI as ROI
    participant DQ as Data Quality
    participant AI as AI Recs
    participant RB as Report Builder
    participant PDF as PDF Engine

    API->>Orch: start(report_id, url)
    Orch->>V: run
    V-->>Orch: validated_url
    Orch->>C: run
    C-->>Orch: crawl
    Orch->>P: run
    P-->>Orch: parsed
    par Fan-out
        Orch->>SEO: run
        Orch->>PERF: run
        Orch->>SEC: run
        Orch->>A11Y: run
    end
    SEO-->>Orch: findings
    PERF-->>Orch: findings
    SEC-->>Orch: findings
    A11Y-->>Orch: findings
    Orch->>HS: run
    HS-->>Orch: scores
    Orch->>BI: run
    BI-->>Orch: issues
    Orch->>ROI: run
    ROI-->>Orch: roi issues
    Orch->>DQ: run
    DQ-->>Orch: ai_payload
    Orch->>AI: run
    AI-->>Orch: recommendations
    Orch->>RB: run
    RB-->>Orch: report JSON
    Orch->>PDF: run (async ok)
    PDF-->>Orch: pdf_url
```

### 21.4 Event Hooks (Optional Future)

`engine.completed`, `engine.failed`, `pipeline.completed` — for workers/UI. MVP may use DB status polling only.

---

## 22. Data Contracts

### 22.1 Contract Map

| From → To | Contract |
|---|---|
| URL Validation → Crawler | `engine.url_validation.output.v1` |
| Crawler → Parser / Security / Perf | `engine.crawler.output.v1` |
| Parser → SEO / A11y / Security | `engine.html_parser.output.v1` |
| SEO/Perf/Sec/A11y → Health Score | `engine.*.output.v1` findings |
| Health Score → Business Impact | `engine.health_score.output.v1` |
| Business Impact → ROI | `engine.business_impact.output.v1` |
| ROI + scores + findings → DQ | combined DQ input v1 |
| DQ → AI | `ai.prompt_payload.v1` |
| AI + DQ → Report Builder | recommendation + dq outputs |
| Report Builder → PDF / API / FE | `report.v1` |

### 22.2 Compatibility Rules

| Rule | Detail |
|---|---|
| Additive changes | New optional fields OK within `vN` |
| Breaking changes | Bump `vN→vN+1`; orchestrator dual-read during migration |
| Unknown fields | Consumers ignore; producers `extra=forbid` on ingress where safety matters |
| Registry | Publish JSON Schema under `packages/types` |

### 22.3 Report Issue Contract (Final)

```json
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
```

---

## 23. Logging

### 23.1 Structured Logging

Every log line is JSON:

```json
{
  "ts": "2026-07-12T10:15:02.042Z",
  "level": "info",
  "service": "sitepilot-api",
  "engine": "crawler",
  "report_id": "rep_9f3ac21e",
  "job_id": "job_123",
  "trace_id": "tr_abc",
  "event": "engine_completed",
  "duration_ms": 1104,
  "status": "success"
}
```

### 23.2 Log Levels

| Level | Use |
|---|---|
| `debug` | Fixture-level detail (disabled in prod default) |
| `info` | Engine start/complete, cache hit/miss |
| `warn` | Soft-fail, renormalization, AI fallback |
| `error` | Hard-fail engine errors |
| `security` | SSRF blocks, auth anomalies (or `error` + `security=true`) |

### 23.3 Audit Logs

Retain immutable audit events for:

- Report created / completed / failed
- PDF generated / downloaded (metadata only)
- Scoring config version used
- Prompt version used
- SSRF blocks

Retention: per compliance policy (default ≥ 90 days).

> [!NOTE]
> Never log raw HTML, cookies, Authorization headers, or full LLM prompts containing customer PII at info level. Prompt hashes + versions are enough for most audits.

---

## 24. Caching

### 24.1 Redis

Primary cache/queue backing store for MVP.

### 24.2 TTL Matrix

| Key pattern | TTL | Notes |
|---|---|---|
| `url_validation:v1:{canon}` | 15m | Success |
| `crawl:v1:{hash}` | 24h | Align report cache |
| `perf:v1:{strategy}:{hash}` | 24h | Expensive |
| `brokenlink:v1:{target}` | 24h | SEO sub-cache |
| `report:v1:{canon}` | 24h | Full report reuse |
| `ai:v1:{prompt_hash}` | 24h | Optional |
| `pdf:v1:{report_hash}` | 7d | Object meta |

### 24.3 Cache Keys

Always include **schema/version** and **canonical URL hash** (SHA-256). Never use raw URLs as keys.

### 24.4 Invalidation

| Trigger | Action |
|---|---|
| TTL expiry | Natural |
| Force refresh flag | Delete crawl+perf+report keys for host/URL |
| Config version bump | Do not reuse AI/score caches across incompatible config |
| Security incident | Flush URL validation negative caches as needed |

---

## 25. Observability

### 25.1 Metrics

| Metric | Type | Labels |
|---|---|---|
| `engine_duration_ms` | histogram | engine, status |
| `engine_runs_total` | counter | engine, status |
| `pipeline_duration_ms` | histogram | status |
| `ai_fallback_total` | counter | reason |
| `ssrf_block_total` | counter | — |
| `cache_hit_total` | counter | cache_name |
| `psi_errors_total` | counter | code |

### 25.2 Tracing

OpenTelemetry spans:

- `pipeline.run`
- `engine.{name}.run`
- external: `http.psi`, `http.origin`, `llm.openai`

Propagate `trace_id` / `report_id` as attributes.

### 25.3 Monitoring

Alert examples:

- p95 pipeline > 45s for 15m
- AI fallback rate > 5%
- SSRF block spike
- Worker queue depth > threshold

### 25.4 Health Checks

| Endpoint | Checks |
|---|---|
| `GET /api/v1/health` | Process up |
| Readiness | Postgres + Redis reachable |
| Worker health | Heartbeat key fresh |

---

## 26. Error Handling

### 26.1 Retries

| Layer | Policy |
|---|---|
| Transient HTTP | Exponential backoff + jitter |
| LLM | 1 retry then provider failover |
| Browser crash | 1 relaunch then soft-fail Performance |
| Non-retryable validation/SSRF | Never retry |

### 26.2 Circuit Breakers

| Dependency | Breaker |
|---|---|
| PSI | Open after N failures → Lighthouse-only |
| OpenAI | Open → Gemini → templates |
| Origin crawl host | Per-host cool-down on repeated timeouts |

### 26.3 Partial Reports

Allowed when:

- Performance soft-failed and renormalization enabled
- AI fell back to templates
- DQ completeness ≥ threshold but some gaps listed

Dashboard must show banners for gaps.

### 26.4 Graceful Failures

| Failure | UX |
|---|---|
| URL validation fail | Immediate 400/422 |
| Crawl fail | Report `failed` with reason |
| Partial analysis | `complete_with_warnings` |
| PDF fail | Dashboard OK; PDF retry available |

---

## 27. Testing

### 27.1 Unit

Pure functions: normalization, penalties, mapping, DQ rules, SSRF classifiers.

### 27.2 Integration

Wiremock origins; sandbox PSI recordings; Redis/Postgres testcontainers.

### 27.3 Contract

JSON Schema validation for every `engine.*.output.vN` fixture in CI.

### 27.4 Performance

Budget tests: parser < 150ms on fixtures; pipeline p95 gate in staging.

### 27.5 Security

SSRF redirect suites; secret redaction tests; header injection fixtures.

### 27.6 Load Testing

- Concurrent analyses ramp
- Browser pool saturation behavior
- Queue backlog + timeout behavior

### 27.7 Golden Pipeline Tests

Fixed crawl fixtures → expected scores + stable issue IDs (AI mocked).

---

## 28. Security

### 28.1 SSRF Protection

Mandatory on URL Validation, Crawler redirects, broken-link checks, and any future outbound fetch. See Engine 1 controls.

### 28.2 Input Validation

Pydantic `extra=forbid` on public API; URL length caps; content-type allowlists.

### 28.3 Secrets Management

API keys only in env / platform secret manager. Never in repo or logs.

### 28.4 Rate Limiting

Per-IP analysis limits; per-host crawl politeness; PSI/LLM quotas.

### 28.5 OWASP Best Practices

| Area | Practice |
|---|---|
| Injection | No shelling out on URLs; parameterized DB |
| XSS | PDF/dashboard escape user-derived strings |
| Security misconfig | Harden headers on our own app |
| Broken access | Signed PDF URLs; future authz on reports |
| SSRF | First-class control |
| Logging | No sensitive data leakage |

---

## 29. Future Engines

| Engine | Purpose |
|---|---|
| **Competitor Intelligence Engine** | Compare health/SEO posture vs competitor URLs |
| **Website Monitoring Engine** | Scheduled re-scans, drift alerts, trend scores |
| **Content Optimization Engine** | On-page content clarity / intent alignment suggestions |
| **AI Chat Assistant Engine** | Conversational Q&A over a single report (grounded) |
| **Keyword Intelligence Engine** | Keyword opportunity overlays (non-MVP) |
| **AI Auto-Fix Engine** | Generate patch PRs / code diffs with human approval |

All future engines must obey §30 principles and publish contracts before integration.

---

## 30. Engine Design Principles

1. **Every engine has one responsibility.**  
2. **Every engine is independently testable.**  
3. **Every engine communicates through contracts.**  
4. **AI explains data.**  
5. **AI never invents data.**  
6. **Every engine should be replaceable.**  
7. **Business logic must remain isolated** (mapping/ROI tables — not scattered in UI or prompts).

> [!TIP]
> If a change requires editing three engines to fix one behavior, the boundary is wrong — stop and split/merge responsibilities via RFC.

---

## 31. Engineering Roadmap & Contributor Guidance

### 31.1 Implementation Order

Implement engines in dependency order. Do not build AI or PDF before contracts and DQ exist.

```mermaid
gantt
    title SitePilot AI — Engine Implementation Roadmap
    dateFormat  YYYY-MM-DD
    axisFormat  %b %d

    section Foundation
    Orchestrator + contracts + artifact store     :a1, 2026-08-01, 10d
    Engine 1 URL Validation                       :a2, after a1, 5d
    Engine 2 Crawler                              :a3, after a2, 8d
    Engine 3 HTML Parser                          :a4, after a3, 6d

    section Analysis Fan-out
    Engine 4 SEO Intelligence                     :b1, after a4, 10d
    Engine 5 Performance                          :b2, after a4, 12d
    Engine 6 Security                             :b3, after a4, 8d
    Engine 7 Accessibility                        :b4, after a4, 10d

    section Intelligence
    Engine 8 Health Score                         :c1, after b1, 7d
    Engine 9 Business Impact                      :c2, after c1, 8d
    Engine 10 ROI                                 :c3, after c2, 6d
    Engine 11 Data Quality                        :c4, after c3, 8d
    Engine 12 AI Recommendations                   :c5, after c4, 12d

    section Delivery
    Engine 13 Report Builder                      :d1, after c5, 7d
    Engine 14 PDF                                 :d2, after d1, 8d
    Dashboard wiring + e2e hardening              :d3, after d1, 14d
    Production deployment                         :d4, after d2, 7d
    MVP Launch                                    :milestone, after d4, 0d
```

### 31.2 Phase Checklist

| Order | Deliverable | Exit criteria |
|---|---|---|
| 1 | Contracts + orchestrator skeleton | Fixture pipeline runs no-ops |
| 2 | Engines 1–3 | Crawl→parse golden fixtures |
| 3 | Engines 4–7 | Parallel fan-out + findings schemas |
| 4 | Engines 8–10 | Stable scores + business fields |
| 5 | Engine 11 | AI cannot be called without DQ |
| 6 | Engine 12 | JSON recommendations + fallback |
| 7 | Engines 13–14 | Dashboard + PDF from one JSON |
| 8 | Observability/security hardening | Alerts + SSRF suites green |

### 31.3 Best Practices for Future Contributors

1. **Read §4 Engine Standards before writing code.** Copy the template into your engine README.  
2. **Add JSON Schema + golden fixtures in the same PR as behavior changes.**  
3. **Never call sibling engines** — extend the orchestrator.  
4. **Never send raw HTML/headers to the LLM** — only `ai_payload` from DQ.  
5. **Prefer config tables over hardcoding** for weights, mappings, and prompts.  
6. **Version contracts** on breaking changes; dual-read during migration.  
7. **Soft-fail expensive/fragile deps** (PSI/LLM); hard-fail safety (SSRF) and data integrity (DQ).  
8. **Log structured fields**, not prose blobs; redact secrets.  
9. **Keep business copy out of analyzers** — analyzers emit technical findings only.  
10. **Update this spec in the same PR** when behavior changes — code is not the source of truth; the spec is.

### 31.4 Implementation Recommendations

| Area | Recommendation |
|---|---|
| Language | Python engines in `apps/api/app/engines/*` with Pydantic contracts |
| Shared types | Publish to `packages/types` for web consumption |
| Workers | RQ/Celery; one pipeline job with staged checkpoints |
| Feature flags | Per-engine enable/disable for degrade drills |
| Local dev | Fixture mode that skips PSI/LLM network |
| CI | Contract + SSRF + golden pipeline required checks |
| Docs | Link engine PRs to `ENGINE_SPEC.md` section anchors |

> [!NOTE]
> When in doubt: **preserve technical truth, isolate business translation, gate AI behind Data Quality, and assemble once.** That is the SitePilot AI engine architecture.

---

<p align="center">
  <sub>SitePilot AI — Engine Specification (Parts 1 & 2) — Internal Engineering Documentation — Confidential</sub>
</p>

# Report Composer — RULES

## Purpose

Assemble **persisted** Audit Run artifacts into one **UI-ready** `AuditReportDTO` for:

```http
GET /api/v1/audits/{audit_id}/report
POST /api/v1/audits/{audit_id}/report/regenerate
```

The frontend must not filter, sort, group, count, merge, or calculate report data.

## Architecture

- Location: `app/services/report/` (service layer — **not** `app/engines/`)
- Not registered in `AuditPipeline`
- No `Engine` adapter / `EngineResult`
- Reads only via repositories
- Writes projection to `reports` (DATABASE_SPEC §16)

```
AuditPipeline (complete)
        ↓
ReportComposer.compose(audit_id)
        ↓
repositories → builder → AuditReportDTO
        ↓
reports.report_json + report_hash (cacheable projection)
```

## Inputs (persisted only)

| Source | Repository |
|---|---|
| AuditRun | `AuditRepository` |
| Website | `WebsiteRepository` |
| AuditFinding | `FindingRepository` |
| HealthScore | `HealthScoreRepository` |
| Recommendation | `RecommendationRepository` |
| EngineExecution | `EngineExecutionRepository` |

## Readiness

| Audit status | Result |
|---|---|
| `complete` / `complete_with_warnings` | Compose |
| anything else | `409 REPORT_NOT_READY` |
| missing audit | `404 AUDIT_NOT_FOUND` |

## Versioning

Separate **schema** from **revision**:

| Field | Meaning | Changes when |
|---|---|---|
| `schema_version` | JSON contract id (`report.v1`) | Report structure changes |
| `report_version` | Generation counter (integer, never resets) | Content actually changes on regenerate |

- DB column `reports.schema_version` ↔ DTO `schema_version`
- DB column `reports.version` ↔ DTO `report_version`
Legacy Sprint 16 JSON with `metadata.version` is accepted and mapped to `report_version`.
Responses still emit `metadata.version` as a computed alias of `report_version` for back-compat.

## Ordering guarantees

### Category order (canonical — never alphabetical / insertion)

1. SEO  
2. Accessibility  
3. Security  
4. Performance  
5. Business  

Applies to `category_scores`, `category_totals`, `recommendation_totals`, and section assembly.
Outside category order: `quick_wins`, `critical_issues`, `recommendations`, `statistics`, `engine_summary`, `metadata`.

### Findings

Within every list (per-category and global slices):

```
Critical → High → Medium → Low → Info
then rule_id → title → id
```

### Recommendations

```
Priority: Critical → High → Medium → Low
then Business Impact: High → Medium → Low (Critical before High if present)
then Estimated Effort: Low → Medium → High (Very Low before Low; Very High after High)
then Title (alphabetical)
```

Frontend must never sort findings or recommendations.

## Grouping rules

Findings are mapped to category sections via `category` / `engine_name` aliases
(`seo`, `accessibility`, `security`, `performance`, `business`).

Business impacts = findings whose category/engine is `business` (never regenerated).

## Quick wins (report layer)

```
priority == "High"
AND estimated_effort ∈ {"Low", "Very Low"}
```

Distinct from engine `is_quick_win` (impact-based). Report rule is authoritative for this DTO.

## Critical issues

All findings with `severity == "critical"` across categories.

## Statistics

Deterministic counts only — no re-analysis. Extended fields:

| Field | Meaning |
|---|---|
| `pass_count` / `warning_count` / `failed_count` | Finding status tallies |
| `finding_count` / `recommendation_count` | Totals |
| `critical_count` … `info_count` | Severity tallies |
| `category_totals` | Findings per category (canonical order) |
| `recommendation_totals` | Recommendations per category (canonical order) |
| `engine_durations` | Per-engine ms (pipeline engine order) |
| `pipeline_duration` | `audit.duration_ms` or sum of engine durations |

Sprint 16 aliases (`total_findings`, `pipeline_duration_ms`, `findings_by_*`, …) remain for compatibility.

## Report hash

```
report_hash = SHA256(canonical_json(strip_volatile(report_json)))
```

Volatile / non-content fields excluded from the digest:

- `generated_at`, `report_id`, `report_hash`, `report_version`
- Same fields under `metadata.*`

Used for smart regeneration and future Redis caching.

## Regeneration optimization

On `force_regenerate` / `POST .../report/regenerate`:

1. Build fresh report JSON from persisted artifacts  
2. Compute SHA-256  
3. Compare to `reports.report_hash`  

| Result | Action |
|---|---|
| Hash identical | Do **not** rewrite `report_json`; do **not** bump `report_version` |
| Hash different | Update `report_json`, `report_hash`, `generated_at`; `report_version += 1` |

Cached GET (`force_regenerate=False`) returns stored projection when `schema_version` matches.

## Serialization

- Lists are explicitly sorted before emit  
- Category-related dicts keep canonical key order  
- Evidence object keys are sorted  
- Hashing uses key-sorted canonical JSON independently of response key order  

Repeated GETs against unchanged data return the same semantic content.

## Summary generation

Deterministic multi-line string from counts + overall score/grade. **No AI.**

## Future compatibility

- Redis cache can key on `report_hash` without changing DTO shape  
- **Sprint 30 export** (`app/export/`) renders PDF / JSON / CSV from `GetAuditReportUseCase` → `AuditReportDTO` (attachment downloads under `/audits/{id}/export/*`)  
- Object-storage signed PDF URLs remain optional later; exporters must not mutate composer or invent findings  
- AI narrative fields may enrich later schema versions without inventing findings  

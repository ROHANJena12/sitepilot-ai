# Recommendation & Priority Engine — RULES

Deterministic, template-based recommendations. **No LLM. No HTML. No network I/O.**

Configuration version: `recommendation_rules@sprint15`

---

## Inputs

Consumes shared-state analyses only:

| Key | Role |
|---|---|
| `seo_analysis` | Findings |
| `accessibility_analysis` | Findings |
| `security_analysis` | Findings |
| `performance_analysis` | Findings |
| `business_analysis` | Findings |
| `health_analysis` | Penalties + confidence context |

Only findings with status `fail` / `warn` / `error` are actionable (if none, all findings are considered).

---

## Template mapping

1. Exact `finding_id` → `FINDING_TO_TEMPLATE` registry entry.
2. Else prefix fallback (`seo.`, `a11y.`, `sec.`, `perf.`, `biz.`) with a **unique** recommendation id per finding (`rec.*.generic_issue:<finding_id>`).
3. Else generic fallback `rec.generic:<finding_id>`.

Templates supply fixed `title`, `description`, `technical_reason`, `business_reason`, category, base effort, base impact, and related rules. **Never free-text generation.**

---

## Deduplication

Findings that resolve to the **same** `recommendation_id` are merged into one recommendation:

- `affected_findings` = unique finding ids
- `source_count` = number of contributing findings
- Evidence/references retained via source rows at persistence time
- Priority uses the **max severity** across the group and summed health penalties

---

## Dependency resolution

Prerequisite edges (`dependencies.py`):

| Prerequisite | Dependents |
|---|---|
| `rec.sec.enforce_https` | HSTS, secure cookies |
| `rec.seo.add_document_title` | Meta description |
| `rec.seo.fix_h1_hierarchy` | Heading order |

If a recommendation is a prerequisite for other **present** recommendations, it receives a **dependency boost** (0.5–1.0) in the priority formula.

---

## Priority algorithm

Configurable weights (`PRIORITY_WEIGHTS`):

| Component | Default weight | Signal |
|---|---|---|
| `severity` | 0.35 | Max severity among affected findings |
| `health_penalty` | 0.20 | Sum of health `effective_penalty` / `PENALTY_SCALE` (cap 1.0) |
| `business_impact` | 0.15 | Finding id starts with `biz.` (or business category) |
| `security_importance` | 0.15 | `sec.` / trust prefixes, or critical severity |
| `occurrence` | 0.10 | `min(count / OCCURRENCE_CAP, 1)` (`OCCURRENCE_CAP=5`) |
| `dependency` | 0.05 | Prerequisite boost |

```
priority_score = 100 * Σ (weight_i * component_i)   # clamped 0–100
```

Bands (`PRIORITY_THRESHOLDS`):

| Label | Score ≥ |
|---|---|
| Critical | 80 |
| High | 60 |
| Medium | 35 |
| Low | 0 |

---

## Impact estimation

1. Start from template `estimated_impact`.
2. Elevate to **Critical** if any affected finding is critical.
3. Slight elevation when severity is high and template impact is low/medium.

---

## Effort estimation

1. Template `estimated_effort` is authoritative.
2. If many findings merge into one recommendation (≥4 / ≥6), effort may step up one level (Very Low→Low→Medium).

Levels: `Very Low`, `Low`, `Medium`, `High`, `Very High`.

---

## Quick wins

```
is_quick_win = estimated_impact ∈ {Critical, High}
             AND estimated_effort ∈ {Very Low, Low}
```

Exposed as `quick_wins` (recommendation_id list) and `statistics.quick_win_count`.

**High impact** list: impact ∈ {Critical, High}.  
**Long term** list: effort ∈ {High, Very High}.

---

## Confidence

- Template `base_confidence` (exact map typically 90; fallbacks 60–70).
- Exact registry mapping preferred; fallbacks capped ≤70.
- +5 if `health_analysis` present (capped at 100).

---

## Configuration knobs

All in `constants.py`:

- `PRIORITY_WEIGHTS`, `SEVERITY_SCORES`, `PRIORITY_THRESHOLDS`
- `OCCURRENCE_CAP`, `PENALTY_SCALE`
- `QUICK_WIN_IMPACTS`, `QUICK_WIN_EFFORTS`
- `SECURITY_PREFIXES`, `BUSINESS_PREFIXES`
- Template registry in `templates.py`
- Dependency edges in `dependencies.py`

---

## Output

`RecommendationAnalysis` with `recommendations`, `priority_summary`, `quick_wins`, `high_impact`, `long_term`, `statistics`, `configuration_version`.

Shared-state key: `recommendation_analysis`.

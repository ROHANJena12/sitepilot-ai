"""
Health Score Engine — scoring philosophy & configuration (Sprint 13).

## Purpose

Aggregate technical + business findings into **defensible, versioned scores**:

- category scores (0–100)
- weighted overall Website Health Score (0–100)
- letter grade
- completeness-based confidence

Never invents findings. Never inspects HTML. Never performs I/O.

## Scoring pipeline

1. Collect findings from seo / accessibility / security / performance / business
2. Resolve finding weights (`weights.py`)
3. Apply severity multipliers (`multipliers.py`)
4. Apply occurrence caps + diminishing returns (`penalties.py` / `constants.py`)
5. Calculate category scores (`scorecard.py`)
6. Weighted overall score (renormalize if a category is missing)
7. Assign letter grade (`grade.py`)
8. Calculate confidence (`confidence.py`)

## Formula

```
raw_penalty(f) = weight(f) × severity_multiplier(f) × status_factor(f)
effective(f)   = raw_penalty(f) × diminishing(occurrence_index)
category       = max(0, 100 − Σ effective(f))
overall        = Σ weight'(c) × category(c)
```

## Category weights (configurable)

| Category | Weight |
|---|---|
| SEO | 25% |
| Accessibility | 20% |
| Security | 20% |
| Performance | 20% |
| Business | 15% |

> Note: ``ENGINE_SPEC.md`` §14 lists a slightly different default mix (Performance 30%,
> Best Practices 10%). Sprint 13 uses the Business-inclusive mix above; both are
> config-driven and version-stamped via ``SCORING_CONFIG_VERSION``.

## Severity multipliers

| Severity | Multiplier | Effective at default weight 10 |
|---|---|---|
| INFO | 0.0 | 0 |
| LOW | 0.5 | 5 |
| MEDIUM | 1.0 | 10 |
| HIGH | 1.5 | 15 |
| CRITICAL | 2.0 | 20 |

Status factors: fail=1.0, warn=0.5 (`WARN_PENALTY_FACTOR`), info/pass=0.

## Diminishing returns

Identical ``finding.id`` within a category:

| Occurrence | Factor |
|---|---|
| 1st | 1.0 |
| 2nd | 0.5 |
| 3rd | 0.25 |
| 4th | 0.125 |
| 5th | 0.05 |
| >5 | capped out (`OCCURRENCE_CAP`) |

## Letter grades

| Grade | Min score |
|---|---|
| A+ | 97 |
| A | 93 |
| A- | 90 |
| B+ | 87 |
| B | 83 |
| B- | 80 |
| C+ | 77 |
| C | 70 |
| D | 60 |
| F | 0 |

## Confidence model

Objective completeness (not subjective quality):

```
confidence = 100 × (
  0.70 × present_analyses / expected_analyses
+ 0.30 × nonempty_signal
)
```

If all analyses are present and findings are empty (perfect audit), nonempty
credit is treated as full.

## Explainability

Every penalty records: finding id, base weight, severity multiplier, status
factor, occurrence index, diminishing factor, raw + effective penalty.

## Renormalization

Missing categories are excluded and remaining weights are renormalized.
Missing categories are **never** scored as 100 (ENGINE_SPEC §14.6).

## Pipeline

… → Business → **Health Score** (``health``)
"""

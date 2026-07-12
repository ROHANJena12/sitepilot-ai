"""Scorecard — category scores, overall weighted score, renormalization."""

from __future__ import annotations

from app.engines.common.findings import Finding
from app.engines.health.constants import (
    CATEGORY_BASE_SCORE,
    CATEGORY_KEYS,
    CATEGORY_WEIGHTS,
    SCORING_CONFIG_VERSION,
    WEIGHT_SUM_TOLERANCE,
)
from app.engines.health.exceptions import InvalidScoringConfigError
from app.engines.health.penalties import apply_penalties
from app.engines.health.schemas import (
    CategoryScore,
    OverallScore,
    Penalty,
    ScoreBreakdown,
)


def validate_category_weights(weights: dict[str, float] | None = None) -> dict[str, float]:
    """Validate weights sum to ~1.0 and cover all categories."""
    resolved = dict(weights or CATEGORY_WEIGHTS)
    missing = [k for k in CATEGORY_KEYS if k not in resolved]
    if missing:
        raise InvalidScoringConfigError(
            f"Missing category weights: {', '.join(missing)}.",
        )
    total = sum(float(resolved[k]) for k in CATEGORY_KEYS)
    if abs(total - 1.0) > WEIGHT_SUM_TOLERANCE:
        raise InvalidScoringConfigError(
            f"Category weights must sum to 1.0 (±{WEIGHT_SUM_TOLERANCE}), got {total}.",
        )
    return {k: float(resolved[k]) for k in CATEGORY_KEYS}


def score_category(
    *,
    category: str,
    findings: tuple[Finding, ...],
    weight: float,
    present: bool = True,
) -> CategoryScore:
    """Calculate one category score: max(0, 100 - Σ effective penalties)."""
    if not present:
        return CategoryScore(
            category=category,
            score=0.0,
            weight=weight,
            weight_effective=0.0,
            finding_count=0,
            penalty_total=0.0,
            penalties=(),
            present=False,
        )

    penalties = apply_penalties(findings, category=category)
    total = sum(p.effective_penalty for p in penalties)
    score = max(0.0, CATEGORY_BASE_SCORE - total)
    return CategoryScore(
        category=category,
        score=round(score, 2),
        weight=weight,
        weight_effective=weight,  # updated later if renormalized
        finding_count=len(findings),
        penalty_total=round(total, 4),
        penalties=penalties,
        present=True,
    )


def compute_overall(
    categories: tuple[CategoryScore, ...],
) -> tuple[OverallScore, tuple[CategoryScore, ...]]:
    """
    Weighted overall score with renormalization for missing categories.

    Never substitutes 100 for missing categories (ENGINE_SPEC §14.6).
    """
    present = [c for c in categories if c.present]
    excluded = tuple(c.category for c in categories if not c.present)

    if not present:
        empty = tuple(
            c.model_copy(update={"weight_effective": 0.0}) for c in categories
        )
        return OverallScore(score=0.0, renormalized=True, excluded_categories=excluded), empty

    weight_sum = sum(c.weight for c in present)
    renormalized = bool(excluded) or abs(weight_sum - 1.0) > WEIGHT_SUM_TOLERANCE

    updated: list[CategoryScore] = []
    overall = 0.0
    for category in categories:
        if not category.present:
            updated.append(category.model_copy(update={"weight_effective": 0.0}))
            continue
        effective = category.weight / weight_sum if weight_sum else 0.0
        updated.append(category.model_copy(update={"weight_effective": round(effective, 6)}))
        overall += effective * category.score

    return (
        OverallScore(
            score=round(overall, 2),
            renormalized=renormalized,
            excluded_categories=excluded,
        ),
        tuple(updated),
    )


def build_scorecard(
    findings_by_category: dict[str, tuple[Finding, ...]],
    *,
    present_categories: set[str],
    weights: dict[str, float] | None = None,
) -> tuple[ScoreBreakdown, tuple[Penalty, ...]]:
    """Run category scoring + overall aggregation."""
    resolved_weights = validate_category_weights(weights)
    category_scores: list[CategoryScore] = []
    for key in CATEGORY_KEYS:
        category_scores.append(
            score_category(
                category=key,
                findings=findings_by_category.get(key, ()),
                weight=resolved_weights[key],
                present=key in present_categories,
            )
        )

    overall, updated = compute_overall(tuple(category_scores))
    all_penalties: list[Penalty] = []
    for category in updated:
        all_penalties.extend(category.penalties)

    breakdown = ScoreBreakdown(
        categories=updated,
        overall=overall,
        scoring_config_version=SCORING_CONFIG_VERSION,
        category_weights=resolved_weights,
    )
    return breakdown, tuple(all_penalties)

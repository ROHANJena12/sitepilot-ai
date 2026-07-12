"""Health Score core — findings → HealthScoreAnalysis."""

from __future__ import annotations

from app.engines.common.findings import Finding
from app.engines.health.confidence import calculate_confidence
from app.engines.health.grade import assign_grade
from app.engines.health.schemas import HealthScoreAnalysis, HealthStatistics
from app.engines.health.scorecard import build_scorecard


def analyze_health(
    *,
    findings_by_category: dict[str, tuple[Finding, ...]],
    present_categories: set[str],
    present_keys: tuple[str, ...],
    finding_counts: dict[str, int],
    warnings: tuple[str, ...] = (),
) -> HealthScoreAnalysis:
    """
    Execute the full scoring pipeline:

    collect → weights → multipliers → diminishing returns →
    category scores → overall → grade → confidence
    """
    breakdown, penalties = build_scorecard(
        findings_by_category,
        present_categories=present_categories,
    )
    grade = assign_grade(breakdown.overall.score)
    confidence = calculate_confidence(
        present_keys=present_keys,
        finding_counts=finding_counts,
    )

    by_key = {c.category: c.score for c in breakdown.categories}
    stats = HealthStatistics(
        total_findings=sum(finding_counts.values()),
        total_penalties=len(penalties),
        total_penalty_points=round(sum(p.effective_penalty for p in penalties), 4),
        categories_scored=sum(1 for c in breakdown.categories if c.present),
        renormalized=breakdown.overall.renormalized,
    )

    return HealthScoreAnalysis(
        overall_score=breakdown.overall.score,
        seo_score=by_key.get("seo", 0.0),
        accessibility_score=by_key.get("accessibility", 0.0),
        security_score=by_key.get("security", 0.0),
        performance_score=by_key.get("performance", 0.0),
        business_score=by_key.get("business", 0.0),
        grade=grade.grade,
        confidence=confidence.confidence,
        breakdown=breakdown,
        penalties=penalties,
        statistics=stats,
        warnings=warnings,
    )

"""Recommendation generation rules — orchestrates templates, merge, priority."""

from __future__ import annotations

from app.engines.recommendation.constants import (
    HIGH_IMPACT_LEVELS,
    LONG_TERM_EFFORTS,
    QUICK_WIN_EFFORTS,
    QUICK_WIN_IMPACTS,
    RULES_CONFIG_VERSION,
)
from app.engines.recommendation.deduplication import group_findings_by_recommendation
from app.engines.recommendation.dependencies import dependency_boost_for
from app.engines.recommendation.priority import (
    PriorityInputs,
    confidence_for,
    compute_priority_score,
    estimate_effort,
    estimate_impact,
    score_to_priority,
)
from app.engines.recommendation.schemas import (
    PrioritySummary,
    Recommendation,
    RecommendationAnalysis,
    RecommendationStatistics,
)
from app.engines.recommendation.validators import RecommendationInput


def build_recommendations(inp: RecommendationInput) -> RecommendationAnalysis:
    """Deterministic finding → recommendation transform (no LLM, no prose invention)."""
    groups = group_findings_by_recommendation(inp.findings)
    present_ids = {g.recommendation_id for g in groups}

    draft: list[Recommendation] = []
    mapped_exact = 0
    unmapped = 0
    merged = 0

    for group in groups:
        findings = tuple(group.findings)
        if len(findings) > 1:
            merged += 1
        if group.mapped_exact:
            mapped_exact += len(findings)
        else:
            unmapped += len(findings)

        penalty_points = sum(
            inp.penalties_by_finding.get(f.id, 0.0) for f in findings
        )
        dep_boost = dependency_boost_for(group.recommendation_id, present_ids)
        score = compute_priority_score(
            PriorityInputs(
                findings=findings,
                penalty_points=penalty_points,
                dependency_boost=dep_boost,
            )
        )
        priority = score_to_priority(score)
        impact = estimate_impact(group.template, findings)
        effort = estimate_effort(group.template, findings)
        is_quick_win = impact.value in QUICK_WIN_IMPACTS and effort.value in QUICK_WIN_EFFORTS
        conf = confidence_for(
            group.template,
            mapped_exact=group.mapped_exact,
            health_present=inp.health is not None,
        )

        draft.append(
            Recommendation(
                recommendation_id=group.recommendation_id,
                title=group.template.title,
                description=group.template.description,
                technical_reason=group.template.technical_reason,
                business_reason=group.template.business_reason,
                category=group.template.category,
                priority=priority,
                estimated_effort=effort,
                estimated_impact=impact,
                confidence=conf,
                affected_findings=tuple(dict.fromkeys(f.id for f in findings)),
                related_rules=group.template.related_rules,
                priority_score=score,
                is_quick_win=is_quick_win,
                source_count=len(findings),
            )
        )

    # Sort: priority_score desc, then recommendation_id for stability
    draft.sort(key=lambda r: (-r.priority_score, r.recommendation_id))
    recommendations = tuple(draft)

    by_priority = {
        "Critical": 0,
        "High": 0,
        "Medium": 0,
        "Low": 0,
    }
    by_category: dict[str, int] = {}
    for rec in recommendations:
        by_priority[rec.priority.value] = by_priority.get(rec.priority.value, 0) + 1
        by_category[rec.category.value] = by_category.get(rec.category.value, 0) + 1

    quick_wins = tuple(r.recommendation_id for r in recommendations if r.is_quick_win)
    high_impact = tuple(
        r.recommendation_id
        for r in recommendations
        if r.estimated_impact.value in HIGH_IMPACT_LEVELS
    )
    long_term = tuple(
        r.recommendation_id
        for r in recommendations
        if r.estimated_effort.value in LONG_TERM_EFFORTS
    )

    summary = PrioritySummary(
        critical=by_priority["Critical"],
        high=by_priority["High"],
        medium=by_priority["Medium"],
        low=by_priority["Low"],
        total=len(recommendations),
    )
    stats = RecommendationStatistics(
        recommendation_count=len(recommendations),
        quick_win_count=len(quick_wins),
        high_impact_count=len(high_impact),
        long_term_count=len(long_term),
        mapped_finding_count=mapped_exact,
        unmapped_finding_count=unmapped,
        merged_group_count=merged,
        by_category=by_category,
        by_priority=by_priority,
    )

    return RecommendationAnalysis(
        recommendations=recommendations,
        priority_summary=summary,
        quick_wins=quick_wins,
        high_impact=high_impact,
        long_term=long_term,
        statistics=stats,
        warnings=inp.warnings,
        configuration_version=RULES_CONFIG_VERSION,
    )

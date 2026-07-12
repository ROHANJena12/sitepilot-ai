"""Priority, impact, and effort calculation (deterministic, configurable weights)."""

from __future__ import annotations

from dataclasses import dataclass

from app.engines.common.findings import Finding, Severity
from app.engines.recommendation.constants import (
    BUSINESS_PREFIXES,
    OCCURRENCE_CAP,
    PENALTY_SCALE,
    PRIORITY_THRESHOLDS,
    PRIORITY_WEIGHTS,
    SECURITY_PREFIXES,
    SEVERITY_SCORES,
)
from app.engines.recommendation.schemas import EffortLevel, ImpactLevel, PriorityLevel
from app.engines.recommendation.templates import RecommendationTemplate


@dataclass(frozen=True, slots=True)
class PriorityInputs:
    findings: tuple[Finding, ...]
    penalty_points: float
    dependency_boost: float  # 0.0–1.0
    weights: dict[str, float] | None = None


def max_severity(findings: tuple[Finding, ...]) -> str:
    order = {
        Severity.CRITICAL: 5,
        Severity.HIGH: 4,
        Severity.MEDIUM: 3,
        Severity.LOW: 2,
        Severity.INFO: 1,
    }
    if not findings:
        return Severity.INFO.value
    best = max(findings, key=lambda f: order.get(f.severity, 0))
    return best.severity.value


def compute_priority_score(inputs: PriorityInputs) -> float:
    """
    Weighted priority score in 0–100.

    Components (see RULES.md):
    severity, health_penalty, business_impact, security_importance,
    occurrence, dependency.
    """
    weights = dict(PRIORITY_WEIGHTS)
    if inputs.weights:
        weights.update(inputs.weights)

    severity = max_severity(inputs.findings)
    severity_component = SEVERITY_SCORES.get(severity, 0.05)

    penalty_component = min(max(inputs.penalty_points, 0.0) / PENALTY_SCALE, 1.0)

    ids = tuple(f.id for f in inputs.findings)
    business_component = 1.0 if any(fid.startswith(BUSINESS_PREFIXES) for fid in ids) else 0.0
    # Also boost if category looks business-ish via finding category field
    if any(f.category.lower().startswith("business") for f in inputs.findings):
        business_component = max(business_component, 0.7)

    security_component = 1.0 if any(fid.startswith(SECURITY_PREFIXES) for fid in ids) else 0.0
    if severity == Severity.CRITICAL.value:
        security_component = max(security_component, 1.0)

    occurrence_component = min(len(inputs.findings) / float(OCCURRENCE_CAP), 1.0)
    dependency_component = min(max(inputs.dependency_boost, 0.0), 1.0)

    raw = (
        weights["severity"] * severity_component
        + weights["health_penalty"] * penalty_component
        + weights["business_impact"] * business_component
        + weights["security_importance"] * security_component
        + weights["occurrence"] * occurrence_component
        + weights["dependency"] * dependency_component
    )
    # weights sum to 1.0 → raw in [0,1]
    return round(min(max(raw * 100.0, 0.0), 100.0), 2)


def score_to_priority(score: float) -> PriorityLevel:
    for label, threshold in PRIORITY_THRESHOLDS:
        if score >= threshold:
            return PriorityLevel(label)
    return PriorityLevel.LOW


def estimate_impact(
    template: RecommendationTemplate,
    findings: tuple[Finding, ...],
) -> ImpactLevel:
    """Start from template impact; elevate when critical findings are present."""
    base = template.estimated_impact
    sev = max_severity(findings)
    if sev == Severity.CRITICAL.value:
        return ImpactLevel.CRITICAL
    if sev == Severity.HIGH.value and base == ImpactLevel.LOW:
        return ImpactLevel.MEDIUM
    if sev == Severity.HIGH.value and base == ImpactLevel.MEDIUM:
        return ImpactLevel.HIGH
    return base


def estimate_effort(
    template: RecommendationTemplate,
    findings: tuple[Finding, ...],
) -> EffortLevel:
    """
    Template effort is authoritative; slight increase when many distinct findings merge.
    """
    effort = template.estimated_effort
    if len(findings) >= 4 and effort == EffortLevel.VERY_LOW:
        return EffortLevel.LOW
    if len(findings) >= 6 and effort in {EffortLevel.VERY_LOW, EffortLevel.LOW}:
        return EffortLevel.MEDIUM
    return effort


def confidence_for(
    template: RecommendationTemplate,
    *,
    mapped_exact: bool,
    health_present: bool,
) -> int:
    confidence = template.base_confidence
    if not mapped_exact:
        confidence = min(confidence, 70)
    if health_present:
        confidence = min(100, confidence + 5)
    return max(0, min(100, confidence))

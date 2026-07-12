"""Input validation / resolution for the Recommendation engine."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from app.engines.common.findings import Finding
from app.engines.health.schemas import HealthScoreAnalysis, Penalty
from app.engines.recommendation.constants import UPSTREAM_ANALYSIS_KEYS
from app.engines.recommendation.exceptions import InvalidAnalysisError, MissingAnalysisError
from app.pipeline.context import AuditContext

_FINDING_KEYS: tuple[str, ...] = (
    "seo_analysis",
    "accessibility_analysis",
    "security_analysis",
    "performance_analysis",
    "business_analysis",
)


@dataclass(frozen=True, slots=True)
class RecommendationInput:
    findings: tuple[Finding, ...]
    health: HealthScoreAnalysis | None
    penalties_by_finding: dict[str, float]
    present_keys: tuple[str, ...]
    warnings: tuple[str, ...]


def resolve_recommendation_input(context: AuditContext) -> RecommendationInput:
    """
    Consume ONLY analysis objects from shared_state.

    Requires all five finding analyses + health_analysis.
    Never reads Document/HTML/network artifacts.
    """
    missing = [k for k in UPSTREAM_ANALYSIS_KEYS if k not in context.shared_state]
    if missing:
        raise MissingAnalysisError(
            f"Missing upstream analyses: {', '.join(missing)}.",
            missing=tuple(missing),
        )

    findings: list[Finding] = []
    warnings: list[str] = []
    present: list[str] = []

    for key in _FINDING_KEYS:
        analysis = context.shared_state[key]
        findings.extend(_extract_findings(analysis, key=key))
        warnings.extend(_extract_warnings(analysis))
        present.append(key)

    health_raw = context.shared_state["health_analysis"]
    health = _coerce_health(health_raw)
    present.append("health_analysis")
    warnings.extend(_extract_warnings(health))

    penalties = _penalties_by_finding(health)
    # Prefer fail/warn findings for recommendations; skip pass/info-only noise optionally
    actionable = tuple(
        f for f in findings if f.status.value in {"fail", "warn", "error"}
    )
    if not actionable and findings:
        actionable = tuple(findings)

    return RecommendationInput(
        findings=actionable,
        health=health,
        penalties_by_finding=penalties,
        present_keys=tuple(present),
        warnings=tuple(dict.fromkeys(warnings)),
    )


def _extract_findings(analysis: Any, *, key: str) -> list[Finding]:
    if analysis is None:
        raise InvalidAnalysisError(f"{key} is None.")
    raw = getattr(analysis, "findings", None)
    if raw is None and isinstance(analysis, dict):
        raw = analysis.get("findings")
    if raw is None:
        raise InvalidAnalysisError(f"{key} does not expose findings.")
    out: list[Finding] = []
    for item in raw:
        if isinstance(item, Finding):
            out.append(item)
        elif isinstance(item, dict):
            out.append(Finding.model_validate(item))
        else:
            raise InvalidAnalysisError(f"{key} contains a non-Finding entry.")
    return out


def _extract_warnings(analysis: Any) -> list[str]:
    raw = getattr(analysis, "warnings", None)
    if raw is None and isinstance(analysis, dict):
        raw = analysis.get("warnings")
    if not raw:
        return []
    return [str(w) for w in raw]


def _coerce_health(raw: Any) -> HealthScoreAnalysis:
    if isinstance(raw, HealthScoreAnalysis):
        return raw
    if isinstance(raw, dict):
        return HealthScoreAnalysis.model_validate(raw)
    raise InvalidAnalysisError("health_analysis is not a HealthScoreAnalysis.")


def _penalties_by_finding(health: HealthScoreAnalysis) -> dict[str, float]:
    totals: dict[str, float] = {}
    for penalty in health.penalties:
        if isinstance(penalty, Penalty):
            totals[penalty.finding_id] = totals.get(penalty.finding_id, 0.0) + float(
                penalty.effective_penalty
            )
        elif isinstance(penalty, dict):
            fid = str(penalty.get("finding_id", ""))
            if fid:
                totals[fid] = totals.get(fid, 0.0) + float(
                    penalty.get("effective_penalty", 0.0)
                )
    return totals

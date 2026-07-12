"""Validators for Health Score engine inputs."""

from __future__ import annotations

from typing import Any

from app.engines.common.findings import Finding
from app.engines.health.constants import UPSTREAM_ANALYSIS_KEYS
from app.engines.health.exceptions import InvalidAnalysisError, MissingAnalysisError
from app.pipeline.context import AuditContext

ANALYSIS_TO_CATEGORY: dict[str, str] = {
    "seo_analysis": "seo",
    "accessibility_analysis": "accessibility",
    "security_analysis": "security",
    "performance_analysis": "performance",
    "business_analysis": "business",
}


def resolve_health_input(
    context: AuditContext,
) -> tuple[
    dict[str, tuple[Finding, ...]],
    set[str],
    tuple[str, ...],
    dict[str, int],
    tuple[str, ...],
]:
    """
    Collect findings by category from shared_state.

    Returns findings_by_category, present_categories, present_keys,
    finding_counts, warnings.
    """
    missing = [key for key in UPSTREAM_ANALYSIS_KEYS if key not in context.shared_state]
    if missing:
        raise MissingAnalysisError(
            f"Missing upstream analyses: {', '.join(missing)}.",
            missing=tuple(missing),
        )

    findings_by_category: dict[str, tuple[Finding, ...]] = {}
    present_categories: set[str] = set()
    present_keys: list[str] = []
    finding_counts: dict[str, int] = {}
    warnings: list[str] = []

    for key in UPSTREAM_ANALYSIS_KEYS:
        category = ANALYSIS_TO_CATEGORY[key]
        analysis = context.shared_state[key]
        findings = _extract_findings(analysis, key=key)
        findings_by_category[category] = findings
        present_categories.add(category)
        present_keys.append(key)
        finding_counts[category] = len(findings)
        warnings.extend(_extract_warnings(analysis))

    return (
        findings_by_category,
        present_categories,
        tuple(present_keys),
        finding_counts,
        tuple(dict.fromkeys(warnings)),
    )


def _extract_findings(analysis: Any, *, key: str) -> tuple[Finding, ...]:
    if analysis is None:
        raise InvalidAnalysisError(f"{key} is None.")
    raw = getattr(analysis, "findings", None)
    if raw is None and isinstance(analysis, dict):
        raw = analysis.get("findings")
    if raw is None:
        raise InvalidAnalysisError(f"{key} does not expose findings.")

    findings: list[Finding] = []
    for item in raw:
        if isinstance(item, Finding):
            findings.append(item)
        elif isinstance(item, dict):
            findings.append(Finding.model_validate(item))
        else:
            raise InvalidAnalysisError(f"{key} contains a non-Finding entry.")
    return tuple(findings)


def _extract_warnings(analysis: Any) -> tuple[str, ...]:
    raw = getattr(analysis, "warnings", None)
    if raw is None and isinstance(analysis, dict):
        raw = analysis.get("warnings")
    if not raw:
        return ()
    return tuple(str(w) for w in raw)

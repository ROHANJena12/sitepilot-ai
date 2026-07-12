"""Validators for Business engine inputs — analyses only, never Document."""

from __future__ import annotations

from typing import Any

from app.engines.business.constants import UPSTREAM_ANALYSIS_KEYS
from app.engines.business.exceptions import InvalidAnalysisError, MissingAnalysisError
from app.engines.business.input import BusinessInput
from app.engines.common.findings import Finding
from app.pipeline.context import AuditContext


def resolve_business_input(context: AuditContext) -> BusinessInput:
    """
    Collect findings from upstream analysis objects in shared_state.

    Required keys: seo_analysis, accessibility_analysis, security_analysis,
    performance_analysis. Document is intentionally ignored.
    """
    missing = [key for key in UPSTREAM_ANALYSIS_KEYS if key not in context.shared_state]
    if missing:
        raise MissingAnalysisError(
            f"Missing upstream analyses: {', '.join(missing)}.",
            missing=tuple(missing),
        )

    source_findings: list[Finding] = []
    warnings: list[str] = []
    source_counts: dict[str, int] = {}

    for key in UPSTREAM_ANALYSIS_KEYS:
        analysis = context.shared_state[key]
        findings = _extract_findings(analysis, key=key)
        source_counts[key] = len(findings)
        source_findings.extend(findings)
        warnings.extend(_extract_warnings(analysis))

    return BusinessInput(
        source_findings=tuple(source_findings),
        warnings=tuple(dict.fromkeys(warnings)),
        source_counts=source_counts,
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

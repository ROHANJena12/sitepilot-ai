"""
Pure business rules — map technical findings to business findings.

No I/O. No Document. Deterministic templates from ``mappings.py``.
"""

from __future__ import annotations

from collections.abc import Sequence

from app.engines.business.input import BusinessInput
from app.engines.business.mappings import BUSINESS_MAPPINGS, resolve_template
from app.engines.business.schemas import BusinessCategory
from app.engines.common.findings import Finding, FindingStatus, Severity


def apply_business_mappings(inp: BusinessInput) -> tuple[tuple[Finding, ...], tuple[str, ...], int, int]:
    """
    Translate mapped technical findings into business findings.

    Returns ``(business_findings, warnings, mapped_count, unmapped_count)``.
    """
    findings: list[Finding] = []
    warnings: list[str] = list(inp.warnings)
    seen_business_ids: set[str] = set()
    mapped_sources = 0
    unmapped_sources = 0

    for source in inp.source_findings:
        template = resolve_template(source.id)
        if template is None:
            unmapped_sources += 1
            continue

        mapped_sources += 1
        if template.business_id in seen_business_ids:
            # Multiple identical technical issues → enrich evidence, keep one business finding.
            for i, existing in enumerate(findings):
                if existing.id == template.business_id:
                    evidence = dict(existing.evidence)
                    sources = list(evidence.get("source_finding_ids") or [])
                    if source.id not in sources:
                        sources.append(source.id)
                    evidence["source_finding_ids"] = sources
                    evidence["source_count"] = len(sources)
                    findings[i] = existing.model_copy(update={"evidence": evidence})
                    break
            continue

        seen_business_ids.add(template.business_id)
        # Prefer the more severe of template vs source for business urgency.
        severity = _max_severity(template.severity, source.severity)
        description = (
            f"{template.why_it_matters} "
            f"Business consequence: {template.business_consequence} "
            f"Affected area: {template.business_area}. "
            f"Customer impact: {template.customer_impact}"
        )
        findings.append(
            Finding(
                id=template.business_id,
                rule_id=template.rule_id,
                category=template.category.value,
                severity=severity,
                title=template.title,
                description=description,
                location=source.location,
                element=source.element,
                evidence={
                    "source_finding_ids": [source.id],
                    "source_engine_hint": source.id.split(".", 1)[0],
                    "source_title": source.title,
                    "why_it_matters": template.why_it_matters,
                    "business_consequence": template.business_consequence,
                    "business_area": template.business_area,
                    "customer_impact": template.customer_impact,
                    "source_count": 1,
                },
                status=_status_for(severity),
            )
        )

    if unmapped_sources:
        warnings.append(f"UNMAPPED_CHECK:{unmapped_sources}")

    return tuple(findings), tuple(dict.fromkeys(warnings)), mapped_sources, unmapped_sources


def _max_severity(a: Severity, b: Severity) -> Severity:
    order = [
        Severity.INFO,
        Severity.LOW,
        Severity.MEDIUM,
        Severity.HIGH,
        Severity.CRITICAL,
    ]
    return order[max(order.index(a), order.index(b))]


def _status_for(severity: Severity) -> FindingStatus:
    if severity in {Severity.CRITICAL, Severity.HIGH}:
        return FindingStatus.FAIL
    if severity == Severity.MEDIUM:
        return FindingStatus.WARN
    if severity == Severity.LOW:
        return FindingStatus.WARN
    return FindingStatus.INFO


def mapped_source_ids() -> frozenset[str]:
    return frozenset(BUSINESS_MAPPINGS.keys())


# Kept for symmetry with other engines' ALL_RULES pattern.
ALL_RULES: Sequence = (apply_business_mappings,)

# Re-export category for docs/tests
__all__ = [
    "apply_business_mappings",
    "mapped_source_ids",
    "ALL_RULES",
    "BusinessCategory",
]

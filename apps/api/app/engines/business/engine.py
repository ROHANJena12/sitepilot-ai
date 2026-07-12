"""Business Intelligence core — upstream findings → BusinessAnalysis."""

from __future__ import annotations

from collections import Counter

from app.engines.business.input import BusinessInput
from app.engines.business.rules import apply_business_mappings
from app.engines.business.schemas import (
    BusinessAnalysis,
    BusinessCategory,
    BusinessStatistics,
    BusinessSummary,
)
from app.engines.common.findings import Finding


def build_statistics(findings: tuple[Finding, ...]) -> BusinessStatistics:
    conversion = 0
    trust = 0
    ux = 0
    marketing = 0
    compliance = 0
    performance = 0

    for finding in findings:
        cat = finding.category
        if cat in {BusinessCategory.CONVERSION.value, BusinessCategory.REVENUE.value}:
            conversion += 1
        elif cat in {BusinessCategory.TRUST.value, BusinessCategory.BRAND.value}:
            trust += 1
        elif cat in {
            BusinessCategory.UX.value,
            BusinessCategory.ACCESSIBILITY_IMPACT.value,
        }:
            ux += 1
        elif cat in {
            BusinessCategory.MARKETING.value,
            BusinessCategory.SEO_IMPACT.value,
        }:
            marketing += 1
        elif cat == BusinessCategory.COMPLIANCE.value:
            compliance += 1
        elif cat == BusinessCategory.PERFORMANCE_IMPACT.value:
            performance += 1

    return BusinessStatistics(
        conversion_findings=conversion,
        trust_findings=trust,
        ux_findings=ux,
        marketing_findings=marketing,
        compliance_findings=compliance,
        performance_findings=performance,
    )


def build_summary(
    findings: tuple[Finding, ...],
    *,
    source_finding_count: int,
    mapped_source_count: int,
    unmapped_source_count: int,
) -> BusinessSummary:
    by_severity = Counter(f.severity.value for f in findings)
    by_category = Counter(f.category for f in findings)
    if not findings:
        message = "No mapped business findings from upstream technical issues."
    else:
        highish = by_severity.get("critical", 0) + by_severity.get("high", 0)
        message = (
            f"{len(findings)} business finding(s) "
            f"({highish} critical/high) from {mapped_source_count} mapped technical issues."
        )
    return BusinessSummary(
        finding_count=len(findings),
        by_severity=dict(by_severity),
        by_category=dict(by_category),
        source_finding_count=source_finding_count,
        mapped_source_count=mapped_source_count,
        unmapped_source_count=unmapped_source_count,
        message=message,
    )


def analyze_business(inp: BusinessInput) -> BusinessAnalysis:
    """Map technical findings to business findings. Never scores or recommends."""
    findings, warnings, mapped, unmapped = apply_business_mappings(inp)
    return BusinessAnalysis(
        findings=findings,
        warnings=warnings,
        summary=build_summary(
            findings,
            source_finding_count=len(inp.source_findings),
            mapped_source_count=mapped,
            unmapped_source_count=unmapped,
        ),
        statistics=build_statistics(findings),
    )

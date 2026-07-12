"""Business analysis models (findings only — no scores)."""

from __future__ import annotations

from enum import StrEnum
from typing import Any

from pydantic import BaseModel, ConfigDict, Field

from app.engines.common.findings import Finding, FindingStatus, Severity


class BusinessCategory(StrEnum):
    """Business finding categories for Sprint 12."""

    SEO_IMPACT = "SEO Impact"
    TRUST = "Trust"
    ACCESSIBILITY_IMPACT = "Accessibility Impact"
    PERFORMANCE_IMPACT = "Performance Impact"
    CONVERSION = "Conversion"
    UX = "UX"
    BRAND = "Brand"
    COMPLIANCE = "Compliance"
    REVENUE = "Revenue"
    MARKETING = "Marketing"


class BusinessStatistics(BaseModel):
    """Aggregate business finding counts by impact area (no scores)."""

    model_config = ConfigDict(frozen=True)

    conversion_findings: int = 0
    trust_findings: int = 0
    ux_findings: int = 0
    marketing_findings: int = 0
    compliance_findings: int = 0
    performance_findings: int = 0


class BusinessSummary(BaseModel):
    """Human-readable summary of the business analysis."""

    model_config = ConfigDict(frozen=True)

    finding_count: int = 0
    by_severity: dict[str, int] = Field(default_factory=dict)
    by_category: dict[str, int] = Field(default_factory=dict)
    source_finding_count: int = 0
    mapped_source_count: int = 0
    unmapped_source_count: int = 0
    message: str = ""


class BusinessAnalysis(BaseModel):
    """Complete Business Intelligence output — findings only, never a score."""

    model_config = ConfigDict(frozen=True)

    findings: tuple[Finding, ...] = ()
    warnings: tuple[str, ...] = ()
    summary: BusinessSummary = Field(default_factory=BusinessSummary)
    statistics: BusinessStatistics = Field(default_factory=BusinessStatistics)

    def to_payload(self) -> dict[str, Any]:
        return self.model_dump(mode="python")


__all__ = [
    "Finding",
    "FindingStatus",
    "Severity",
    "BusinessAnalysis",
    "BusinessCategory",
    "BusinessStatistics",
    "BusinessSummary",
]

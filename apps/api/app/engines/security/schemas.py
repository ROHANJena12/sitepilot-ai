"""Security analysis models (findings only — no scores)."""

from __future__ import annotations

from enum import StrEnum
from typing import Any

from pydantic import BaseModel, ConfigDict, Field

from app.engines.common.findings import Finding, FindingStatus, Severity


class SecurityCategory(StrEnum):
    """Security finding categories for Sprint 10."""

    HTTP_HEADERS = "HTTP Headers"
    HTTPS = "HTTPS"
    MIXED_CONTENT = "Mixed Content"
    COOKIES = "Cookies"
    SCRIPTS = "Scripts"
    LINKS = "Links"
    IFRAMES = "iframes"
    SECURITY_METADATA = "Security Metadata"
    CONTENT_SECURITY = "Content Security"
    CLICKJACKING = "Clickjacking"
    TRANSPORT_SECURITY = "Transport Security"
    INFORMATION_DISCLOSURE = "Information Disclosure"


class SecurityStatistics(BaseModel):
    """Aggregate security counts (no scores)."""

    model_config = ConfigDict(frozen=True)

    security_headers_present: int = 0
    security_headers_missing: int = 0
    inline_scripts: int = 0
    external_scripts: int = 0
    mixed_content_items: int = 0
    iframes: int = 0
    cookies: int = 0
    insecure_forms: int = 0


class SecuritySummary(BaseModel):
    """Human-readable summary of the security analysis."""

    model_config = ConfigDict(frozen=True)

    finding_count: int = 0
    by_severity: dict[str, int] = Field(default_factory=dict)
    by_category: dict[str, int] = Field(default_factory=dict)
    message: str = ""
    https: bool = False


class SecurityAnalysis(BaseModel):
    """Complete Security Intelligence output — findings only, never a score."""

    model_config = ConfigDict(frozen=True)

    findings: tuple[Finding, ...] = ()
    warnings: tuple[str, ...] = ()
    summary: SecuritySummary = Field(default_factory=SecuritySummary)
    statistics: SecurityStatistics = Field(default_factory=SecurityStatistics)

    def to_payload(self) -> dict[str, Any]:
        return self.model_dump(mode="python")


__all__ = [
    "Finding",
    "FindingStatus",
    "Severity",
    "SecurityAnalysis",
    "SecurityCategory",
    "SecurityStatistics",
    "SecuritySummary",
]

"""Performance analysis models (findings only — no scores)."""

from __future__ import annotations

from enum import StrEnum
from typing import Any

from pydantic import BaseModel, ConfigDict, Field

from app.engines.common.findings import Finding, FindingStatus, Severity


class PerformanceCategory(StrEnum):
    """Performance finding categories for Sprint 11."""

    HTML = "HTML"
    IMAGES = "Images"
    CSS = "CSS"
    JAVASCRIPT = "JavaScript"
    FONTS = "Fonts"
    HTTP_HEADERS = "HTTP Headers"
    CACHING = "Caching"
    COMPRESSION = "Compression"
    NETWORK = "Network"
    DOM = "DOM"
    LOADING = "Loading"
    RENDERING = "Rendering"


class PerformanceStatistics(BaseModel):
    """Aggregate performance counts derived from Document + crawl metadata."""

    model_config = ConfigDict(frozen=True)

    dom_nodes: int = 0
    dom_depth: int = 0
    images: int = 0
    lazy_loaded_images: int = 0
    scripts: int = 0
    external_scripts: int = 0
    stylesheets: int = 0
    external_stylesheets: int = 0
    fonts: int = 0
    external_assets: int = 0
    third_party_domains: int = 0
    resource_hints: int = 0
    html_size: int = 0


class PerformanceSummary(BaseModel):
    """Human-readable summary of the performance analysis."""

    model_config = ConfigDict(frozen=True)

    finding_count: int = 0
    by_severity: dict[str, int] = Field(default_factory=dict)
    by_category: dict[str, int] = Field(default_factory=dict)
    message: str = ""


class PerformanceAnalysis(BaseModel):
    """Complete Performance Intelligence output — findings only, never a score."""

    model_config = ConfigDict(frozen=True)

    findings: tuple[Finding, ...] = ()
    warnings: tuple[str, ...] = ()
    summary: PerformanceSummary = Field(default_factory=PerformanceSummary)
    statistics: PerformanceStatistics = Field(default_factory=PerformanceStatistics)

    def to_payload(self) -> dict[str, Any]:
        return self.model_dump(mode="python")


__all__ = [
    "Finding",
    "FindingStatus",
    "Severity",
    "PerformanceAnalysis",
    "PerformanceCategory",
    "PerformanceStatistics",
    "PerformanceSummary",
]

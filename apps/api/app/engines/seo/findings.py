"""SEO Finding and analysis models (findings only — no scores)."""

from __future__ import annotations

from enum import StrEnum
from typing import Any

from pydantic import BaseModel, ConfigDict, Field

from app.engines.common.findings import Finding, FindingStatus, Severity


class FindingCategory(StrEnum):
    """SEO finding categories for Sprint 8."""

    TITLE = "Title"
    META = "Meta"
    HEADINGS = "Headings"
    LINKS = "Links"
    IMAGES = "Images"
    CANONICAL = "Canonical"
    ROBOTS = "Robots"
    OPEN_GRAPH = "OpenGraph"
    TWITTER = "Twitter"
    STRUCTURED_DATA = "StructuredData"
    LANGUAGE = "Language"
    VIEWPORT = "Viewport"
    CONTENT = "Content"
    INDEXABILITY = "Indexability"


class SeoStatistics(BaseModel):
    """Aggregate counts derived from the Document (no scores)."""

    model_config = ConfigDict(frozen=True)

    number_of_titles: int = 0
    number_of_h1: int = 0
    number_of_images: int = 0
    images_without_alt: int = 0
    internal_links: int = 0
    external_links: int = 0
    structured_data_items: int = 0
    headings: int = 0
    word_count: int = 0


class SeoSummary(BaseModel):
    """Human-readable summary of the SEO analysis."""

    model_config = ConfigDict(frozen=True)

    finding_count: int = 0
    by_severity: dict[str, int] = Field(default_factory=dict)
    by_category: dict[str, int] = Field(default_factory=dict)
    message: str = ""


class SeoAnalysis(BaseModel):
    """
    Complete SEO Intelligence output for one Document.

    Contains findings and statistics only — never Health Score / SEO score.
    """

    model_config = ConfigDict(frozen=True)

    findings: tuple[Finding, ...] = ()
    warnings: tuple[str, ...] = ()
    summary: SeoSummary = Field(default_factory=SeoSummary)
    statistics: SeoStatistics = Field(default_factory=SeoStatistics)

    def to_payload(self) -> dict[str, Any]:
        return self.model_dump(mode="python")


__all__ = [
    "Finding",
    "FindingCategory",
    "FindingStatus",
    "Severity",
    "SeoAnalysis",
    "SeoStatistics",
    "SeoSummary",
]

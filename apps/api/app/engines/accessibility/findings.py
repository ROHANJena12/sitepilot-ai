"""Accessibility Finding and analysis models (findings only — no scores)."""

from __future__ import annotations

from enum import StrEnum
from typing import Any

from pydantic import BaseModel, ConfigDict, Field

from app.engines.common.findings import Finding, FindingStatus, Severity


class AccessibilityCategory(StrEnum):
    """Accessibility finding categories for Sprint 9."""

    IMAGES = "Images"
    FORMS = "Forms"
    BUTTONS = "Buttons"
    LINKS = "Links"
    HEADINGS = "Headings"
    ARIA = "ARIA"
    LANDMARKS = "Landmarks"
    LANGUAGE = "Language"
    TABLES = "Tables"
    MEDIA = "Media"
    NAVIGATION = "Navigation"
    FOCUS = "Focus"
    SEMANTICS = "Semantics"
    DOCUMENTS = "Documents"


class AccessibilityStatistics(BaseModel):
    """Aggregate accessibility counts derived from Document + HTML signals."""

    model_config = ConfigDict(frozen=True)

    images: int = 0
    images_missing_alt: int = 0
    forms: int = 0
    unlabelled_forms: int = 0
    buttons: int = 0
    empty_buttons: int = 0
    links: int = 0
    empty_links: int = 0
    headings: int = 0
    tables: int = 0
    videos: int = 0
    audio: int = 0
    landmarks: int = 0
    aria_attributes: int = 0


class AccessibilitySummary(BaseModel):
    """Human-readable summary of the accessibility analysis."""

    model_config = ConfigDict(frozen=True)

    finding_count: int = 0
    by_severity: dict[str, int] = Field(default_factory=dict)
    by_category: dict[str, int] = Field(default_factory=dict)
    message: str = ""


class AccessibilityAnalysis(BaseModel):
    """
    Complete Accessibility Intelligence output for one Document.

    Findings and statistics only — never an accessibility score.
    """

    model_config = ConfigDict(frozen=True)

    findings: tuple[Finding, ...] = ()
    warnings: tuple[str, ...] = ()
    summary: AccessibilitySummary = Field(default_factory=AccessibilitySummary)
    statistics: AccessibilityStatistics = Field(default_factory=AccessibilityStatistics)

    def to_payload(self) -> dict[str, Any]:
        return self.model_dump(mode="python")


__all__ = [
    "AccessibilityAnalysis",
    "AccessibilityCategory",
    "AccessibilityStatistics",
    "AccessibilitySummary",
    "Finding",
    "FindingStatus",
    "Severity",
]

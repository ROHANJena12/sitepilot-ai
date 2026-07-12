"""Accessibility Intelligence Engine — Document → findings (ENGINE_SPEC §12)."""

from __future__ import annotations

from app.engines.accessibility.adapter import AccessibilityEngine
from app.engines.accessibility.engine import analyze_document
from app.engines.accessibility.exceptions import (
    AccessibilityError,
    InvalidDocumentError,
    MissingDocumentError,
)
from app.engines.accessibility.findings import (
    AccessibilityAnalysis,
    AccessibilityCategory,
    AccessibilityStatistics,
    AccessibilitySummary,
    Finding,
    FindingStatus,
    Severity,
)

__all__ = [
    "AccessibilityEngine",
    "analyze_document",
    "AccessibilityAnalysis",
    "AccessibilityCategory",
    "AccessibilityStatistics",
    "AccessibilitySummary",
    "Finding",
    "FindingStatus",
    "Severity",
    "AccessibilityError",
    "MissingDocumentError",
    "InvalidDocumentError",
]

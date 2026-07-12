"""SEO Intelligence Engine — Document → findings (ENGINE_SPEC §9)."""

from __future__ import annotations

from app.engines.seo.adapter import SeoEngine
from app.engines.seo.engine import analyze_document
from app.engines.seo.exceptions import InvalidDocumentError, MissingDocumentError, SeoError
from app.engines.seo.findings import (
    Finding,
    FindingCategory,
    FindingStatus,
    SeoAnalysis,
    SeoStatistics,
    SeoSummary,
    Severity,
)

__all__ = [
    "SeoEngine",
    "analyze_document",
    "SeoAnalysis",
    "SeoStatistics",
    "SeoSummary",
    "Finding",
    "FindingCategory",
    "FindingStatus",
    "Severity",
    "SeoError",
    "MissingDocumentError",
    "InvalidDocumentError",
]

"""Security Intelligence Engine — Document + crawl metadata → findings (ENGINE_SPEC §11)."""

from __future__ import annotations

from app.engines.security.adapter import SecurityEngine
from app.engines.security.engine import analyze_security
from app.engines.security.exceptions import (
    InvalidDocumentError,
    MissingCrawlMetadataError,
    MissingDocumentError,
    SecurityError,
)
from app.engines.security.schemas import (
    Finding,
    FindingStatus,
    SecurityAnalysis,
    SecurityCategory,
    SecurityStatistics,
    SecuritySummary,
    Severity,
)

__all__ = [
    "SecurityEngine",
    "analyze_security",
    "SecurityAnalysis",
    "SecurityCategory",
    "SecurityStatistics",
    "SecuritySummary",
    "Finding",
    "FindingStatus",
    "Severity",
    "SecurityError",
    "MissingDocumentError",
    "InvalidDocumentError",
    "MissingCrawlMetadataError",
]

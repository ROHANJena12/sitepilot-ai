"""Performance Intelligence Engine — static Document + crawl findings (Sprint 11)."""

from __future__ import annotations

from app.engines.performance.adapter import PerformanceEngine
from app.engines.performance.engine import analyze_performance
from app.engines.performance.exceptions import (
    InvalidDocumentError,
    MissingCrawlMetadataError,
    MissingDocumentError,
    PerformanceError,
)
from app.engines.performance.schemas import (
    Finding,
    FindingStatus,
    PerformanceAnalysis,
    PerformanceCategory,
    PerformanceStatistics,
    PerformanceSummary,
    Severity,
)

__all__ = [
    "PerformanceEngine",
    "analyze_performance",
    "PerformanceAnalysis",
    "PerformanceCategory",
    "PerformanceStatistics",
    "PerformanceSummary",
    "Finding",
    "FindingStatus",
    "Severity",
    "PerformanceError",
    "MissingDocumentError",
    "InvalidDocumentError",
    "MissingCrawlMetadataError",
]

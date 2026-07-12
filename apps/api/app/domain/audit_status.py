"""Audit Run status — DATABASE_SPEC §9 / API_SPEC §6.3 + Sprint 14 engine phases."""

from __future__ import annotations

from enum import StrEnum


class AuditStatus(StrEnum):
    PENDING = "pending"
    VALIDATING = "validating"
    CRAWLING = "crawling"
    PARSING = "parsing"
    SEO = "seo"
    ACCESSIBILITY = "accessibility"
    SECURITY = "security"
    PERFORMANCE = "performance"
    BUSINESS = "business"
    HEALTH = "health"
    RECOMMENDATION = "recommendation"
    # Coarse / legacy API_SPEC phases (still valid)
    ANALYZING = "analyzing"
    SCORING = "scoring"
    ENRICHING = "enriching"
    BUILDING_REPORT = "building_report"
    COMPLETE = "complete"
    COMPLETE_WITH_WARNINGS = "complete_with_warnings"
    FAILED = "failed"
    CANCELLED = "cancelled"


AUDIT_STATUS_QUEUED = AuditStatus.PENDING
AUDIT_STATUS_RUNNING = AuditStatus.ANALYZING
AUDIT_STATUS_COMPLETED = AuditStatus.COMPLETE

AUDIT_STATUS_VALUES = tuple(status.value for status in AuditStatus)

TERMINAL_STATUSES = frozenset(
    {
        AuditStatus.COMPLETE,
        AuditStatus.COMPLETE_WITH_WARNINGS,
        AuditStatus.FAILED,
        AuditStatus.CANCELLED,
    }
)

# Pipeline engine → audit status while that engine runs / after it starts.
ENGINE_STATUS_MAP: dict[str, AuditStatus] = {
    "url_validation": AuditStatus.VALIDATING,
    "crawler": AuditStatus.CRAWLING,
    "parser": AuditStatus.PARSING,
    "seo": AuditStatus.SEO,
    "accessibility": AuditStatus.ACCESSIBILITY,
    "security": AuditStatus.SECURITY,
    "performance": AuditStatus.PERFORMANCE,
    "business": AuditStatus.BUSINESS,
    "health": AuditStatus.HEALTH,
    "recommendation": AuditStatus.RECOMMENDATION,
}

# Progress percent after each engine completes successfully.
ENGINE_PROGRESS_MAP: dict[str, int] = {
    "url_validation": 10,
    "crawler": 20,
    "parser": 30,
    "seo": 40,
    "accessibility": 50,
    "security": 60,
    "performance": 70,
    "business": 80,
    "health": 90,
    "recommendation": 100,
}

"""Report Composer constants."""

from __future__ import annotations

from typing import Final

SCHEMA_VERSION: Final[str] = "report.v1"
SERVICE_NAME: Final[str] = "report_composer"

# Audit statuses that may receive a composed report.
READY_AUDIT_STATUSES: Final[frozenset[str]] = frozenset(
    {"complete", "complete_with_warnings"}
)

# Finding severity sort order (Critical first).
SEVERITY_SORT_ORDER: Final[dict[str, int]] = {
    "critical": 0,
    "high": 1,
    "medium": 2,
    "low": 3,
    "info": 4,
}

# Recommendation priority / impact / effort sort orders.
PRIORITY_SORT_ORDER: Final[dict[str, int]] = {
    "Critical": 0,
    "High": 1,
    "Medium": 2,
    "Low": 3,
}

IMPACT_SORT_ORDER: Final[dict[str, int]] = {
    "Critical": 0,
    "High": 1,
    "Medium": 2,
    "Low": 3,
}

# Lower effort first (quick fixes surface earlier).
EFFORT_SORT_ORDER: Final[dict[str, int]] = {
    "Very Low": 0,
    "Low": 1,
    "Medium": 2,
    "High": 3,
    "Very High": 4,
}

# Canonical category section keys — NEVER alphabetical / insertion order.
CATEGORY_SECTIONS: Final[tuple[str, ...]] = (
    "seo",
    "accessibility",
    "security",
    "performance",
    "business",
)

# Pipeline engine order for deterministic engine_durations keys.
ENGINE_DURATION_ORDER: Final[tuple[str, ...]] = (
    "url_validation",
    "crawler",
    "parser",
    "seo",
    "accessibility",
    "security",
    "performance",
    "business",
    "health",
    "recommendation",
)

# Map persisted finding category / engine hints → section key.
CATEGORY_ALIASES: Final[dict[str, str]] = {
    "seo": "seo",
    "seo_impact": "seo",
    "accessibility": "accessibility",
    "a11y": "accessibility",
    "accessibility_impact": "accessibility",
    "security": "security",
    "performance": "performance",
    "perf": "performance",
    "business": "business",
    "business_impact": "business",
    "marketing": "business",
    "conversion": "business",
    "ux": "business",
    "trust": "business",
    "brand": "business",
    "compliance": "business",
    "revenue": "business",
}

ENGINE_TO_CATEGORY: Final[dict[str, str]] = {
    "seo": "seo",
    "accessibility": "accessibility",
    "security": "security",
    "performance": "performance",
    "business": "business",
}

# Sprint 16 quick-win rule (report layer): High priority + Low effort band.
QUICK_WIN_PRIORITIES: Final[frozenset[str]] = frozenset({"High"})
QUICK_WIN_EFFORTS: Final[frozenset[str]] = frozenset({"Low", "Very Low"})

CRITICAL_SEVERITY: Final[str] = "critical"

# Fields excluded from content hash (volatile / assigned after build).
# report_version / version are excluded so identical content after a prior bump still matches.
HASH_EXCLUDE_PATHS: Final[frozenset[str]] = frozenset(
    {
        "generated_at",
        "report_id",
        "report_hash",
        "report_version",
        "version",
        "metadata.generated_at",
        "metadata.report_id",
        "metadata.report_hash",
        "metadata.report_version",
        "metadata.version",
    }
)

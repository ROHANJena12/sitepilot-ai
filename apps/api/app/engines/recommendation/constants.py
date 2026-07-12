"""Recommendation & Priority Engine constants."""

from __future__ import annotations

from typing import Final

ENGINE_NAME: Final[str] = "recommendation"
SCHEMA_VERSION: Final[str] = "engine.recommendation.output.v1"
RULES_CONFIG_VERSION: Final[str] = "recommendation_rules@sprint15"
PROVIDER: Final[str] = "rules"
MODEL_USED: Final[str] = "rules:v1"

UPSTREAM_ANALYSIS_KEYS: Final[tuple[str, ...]] = (
    "seo_analysis",
    "accessibility_analysis",
    "security_analysis",
    "performance_analysis",
    "business_analysis",
    "health_analysis",
)

# Shared-state key written by this engine.
ANALYSIS_STATE_KEY: Final[str] = "recommendation_analysis"

# Priority formula weights (must remain configurable; documented in RULES.md).
PRIORITY_WEIGHTS: Final[dict[str, float]] = {
    "severity": 0.35,
    "health_penalty": 0.20,
    "business_impact": 0.15,
    "security_importance": 0.15,
    "occurrence": 0.10,
    "dependency": 0.05,
}

SEVERITY_SCORES: Final[dict[str, float]] = {
    "critical": 1.0,
    "high": 0.8,
    "medium": 0.5,
    "low": 0.25,
    "info": 0.05,
}

# Map normalized priority_score (0–100) → Priority label.
PRIORITY_THRESHOLDS: Final[tuple[tuple[str, float], ...]] = (
    ("Critical", 80.0),
    ("High", 60.0),
    ("Medium", 35.0),
    ("Low", 0.0),
)

# Quick-win: high/critical impact AND very-low/low effort.
QUICK_WIN_IMPACTS: Final[frozenset[str]] = frozenset({"Critical", "High"})
QUICK_WIN_EFFORTS: Final[frozenset[str]] = frozenset({"Very Low", "Low"})

# High-impact bucket for summary lists.
HIGH_IMPACT_LEVELS: Final[frozenset[str]] = frozenset({"Critical", "High"})

# Long-term: high / very-high effort.
LONG_TERM_EFFORTS: Final[frozenset[str]] = frozenset({"High", "Very High"})

# Occurrence contribution: min(count / OCCURRENCE_CAP, 1.0)
OCCURRENCE_CAP: Final[int] = 5

# Security categories / finding prefixes that receive security_importance boost.
SECURITY_PREFIXES: Final[tuple[str, ...]] = ("sec.", "biz.trust.", "biz.revenue.")

# Business finding prefixes that receive business_impact boost.
BUSINESS_PREFIXES: Final[tuple[str, ...]] = ("biz.",)

# Health penalty points are scaled: min(penalty / PENALTY_SCALE, 1.0)
PENALTY_SCALE: Final[float] = 20.0

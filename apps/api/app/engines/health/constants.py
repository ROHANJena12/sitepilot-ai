"""Health Score Engine constants — category weights, caps, grade thresholds."""

from __future__ import annotations

from typing import Final

ENGINE_NAME: Final[str] = "health"
SCHEMA_VERSION: Final[str] = "engine.health_score.output.v1"
SCORING_CONFIG_VERSION: Final[str] = "scoring_config@sprint13"

# Shared-state keys for upstream analyses (required for full confidence).
UPSTREAM_ANALYSIS_KEYS: Final[tuple[str, ...]] = (
    "seo_analysis",
    "accessibility_analysis",
    "security_analysis",
    "performance_analysis",
    "business_analysis",
)

# Category score keys used throughout the engine.
CATEGORY_KEYS: Final[tuple[str, ...]] = (
    "seo",
    "accessibility",
    "security",
    "performance",
    "business",
)

# Default category weights (must sum to 1.0). Sprint 13 defaults.
CATEGORY_WEIGHTS: Final[dict[str, float]] = {
    "seo": 0.25,
    "accessibility": 0.20,
    "security": 0.20,
    "performance": 0.20,
    "business": 0.15,
}

# Starting score for each category before penalties.
CATEGORY_BASE_SCORE: Final[float] = 100.0

# Maximum identical finding_id contributions counted per category (hard cap).
OCCURRENCE_CAP: Final[int] = 5

# Diminishing return factors by occurrence index (0-based) within a finding_id.
# Index 0 = first occurrence (full), then decay. Extra indices use the last factor.
DIMINISHING_RETURNS: Final[tuple[float, ...]] = (1.0, 0.5, 0.25, 0.125, 0.05)

# Warn findings contribute this fraction of a fail penalty (ENGINE_SPEC warn_penalty_factor).
WARN_PENALTY_FACTOR: Final[float] = 0.5

# Info/pass findings contribute nothing.
INFO_STATUS_FACTOR: Final[float] = 0.0
PASS_STATUS_FACTOR: Final[float] = 0.0

# Letter grade thresholds (score >= threshold → grade), descending.
GRADE_THRESHOLDS: Final[tuple[tuple[str, float], ...]] = (
    ("A+", 97.0),
    ("A", 93.0),
    ("A-", 90.0),
    ("B+", 87.0),
    ("B", 83.0),
    ("B-", 80.0),
    ("C+", 77.0),
    ("C", 70.0),
    ("D", 60.0),
    ("F", 0.0),
)

# Confidence model weights (sum to 1.0).
CONFIDENCE_ANALYSIS_PRESENCE_WEIGHT: Final[float] = 0.70
CONFIDENCE_NONEMPTY_CATEGORY_WEIGHT: Final[float] = 0.30

# Weight sum tolerance for config validation.
WEIGHT_SUM_TOLERANCE: Final[float] = 0.001

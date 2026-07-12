"""Business Intelligence Engine constants."""

from __future__ import annotations

from typing import Final

ENGINE_NAME: Final[str] = "business"
SCHEMA_VERSION: Final[str] = "engine.business.output.v1"

# Shared-state keys for upstream analysis objects.
UPSTREAM_ANALYSIS_KEYS: Final[tuple[str, ...]] = (
    "seo_analysis",
    "accessibility_analysis",
    "security_analysis",
    "performance_analysis",
)

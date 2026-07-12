"""Explicit entity types for AI persistence (closed set — not free-form strings)."""

from __future__ import annotations

from enum import StrEnum

from app.ai.features import AIFeature


class AIEntityType(StrEnum):
    """
    Persisted AI artifact entity types.

    Aligns 1:1 with ``AIFeature`` values but is intentionally separate so
    persistence identity cannot drift into prompt-id aliases.
    """

    FINDING = "finding"
    RECOMMENDATION = "recommendation"
    EXECUTIVE_SUMMARY = "executive_summary"
    BUSINESS_SUMMARY = "business_summary"
    QUICK_WIN = "quick_win"


def entity_type_for_feature(feature: AIFeature | str) -> AIEntityType:
    """Map ``AIFeature`` → ``AIEntityType`` (same wire values)."""
    if isinstance(feature, AIFeature):
        return AIEntityType(feature.value)
    return AIEntityType(str(feature))

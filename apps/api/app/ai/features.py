"""Canonical AI feature registry and generation identity aliases."""

from __future__ import annotations

from enum import StrEnum
from uuid import UUID

# Immutable execution identifier (created once per GenerationSession.start()).
GenerationId = UUID


class AIFeature(StrEnum):
    """
    Canonical internal feature identifiers.

    Distinct from prompt template ids / filenames:
    ``AIFeature.FINDING`` → prompt file ``finding_explanation.md``.
    """

    FINDING = "finding"
    RECOMMENDATION = "recommendation"
    EXECUTIVE_SUMMARY = "executive_summary"
    BUSINESS_SUMMARY = "business_summary"
    QUICK_WIN = "quick_win"


# Prompt template ids (filename stems) — do not rename without migrating files.
FEATURE_PROMPT_IDS: dict[AIFeature, str] = {
    AIFeature.FINDING: "finding_explanation",
    AIFeature.RECOMMENDATION: "recommendation",
    AIFeature.EXECUTIVE_SUMMARY: "executive_summary",
    AIFeature.BUSINESS_SUMMARY: "business_summary",
    AIFeature.QUICK_WIN: "quick_win",
}

PROMPT_ID_TO_FEATURE: dict[str, AIFeature] = {
    prompt_id: feature for feature, prompt_id in FEATURE_PROMPT_IDS.items()
}


def resolve_feature(value: AIFeature | str) -> AIFeature:
    """
    Resolve a feature from ``AIFeature``, feature value, or legacy prompt id.

    Examples: ``AIFeature.FINDING``, ``\"finding\"``, ``\"finding_explanation\"``.
    """
    if isinstance(value, AIFeature):
        return value
    try:
        return AIFeature(value)
    except ValueError:
        pass
    feature = PROMPT_ID_TO_FEATURE.get(value)
    if feature is not None:
        return feature
    raise KeyError(
        f"Unknown AI feature '{value}'. "
        f"Expected one of {', '.join(f.value for f in AIFeature)} "
        f"or prompt ids {', '.join(FEATURE_PROMPT_IDS.values())}."
    )


def prompt_id_for(feature: AIFeature | str) -> str:
    """Return the prompt template id for a feature (filename stem)."""
    return FEATURE_PROMPT_IDS[resolve_feature(feature)]

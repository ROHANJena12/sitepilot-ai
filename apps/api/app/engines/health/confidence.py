"""Confidence calculation from analysis completeness (objective, not subjective)."""

from __future__ import annotations

from app.engines.health.constants import (
    CATEGORY_KEYS,
    CONFIDENCE_ANALYSIS_PRESENCE_WEIGHT,
    CONFIDENCE_NONEMPTY_CATEGORY_WEIGHT,
    UPSTREAM_ANALYSIS_KEYS,
)
from app.engines.health.schemas import ConfidenceResult


def calculate_confidence(
    *,
    present_keys: tuple[str, ...],
    finding_counts: dict[str, int],
) -> ConfidenceResult:
    """
    Confidence is based on expected analysis presence and whether categories
    produced findings (empty findings still count as present analyses).

    confidence =
      70% * (analyses_present / analyses_expected)
    + 30% * (categories_with_any_signal / categories)
      where "signal" means the analysis object was present (scored),
      and nonempty bonus uses finding_counts > 0 as quality signal.
    """
    expected = len(UPSTREAM_ANALYSIS_KEYS)
    present = sum(1 for key in UPSTREAM_ANALYSIS_KEYS if key in present_keys)
    presence_ratio = present / expected if expected else 0.0

    # Nonempty: categories that had at least one finding (informational completeness).
    nonempty = sum(1 for key in CATEGORY_KEYS if finding_counts.get(key, 0) > 0)
    # If all categories are present but empty (perfect page), treat as full nonempty credit.
    if present == expected and nonempty == 0:
        nonempty_ratio = 1.0
    else:
        nonempty_ratio = nonempty / len(CATEGORY_KEYS)

    confidence = 100.0 * (
        CONFIDENCE_ANALYSIS_PRESENCE_WEIGHT * presence_ratio
        + CONFIDENCE_NONEMPTY_CATEGORY_WEIGHT * nonempty_ratio
    )
    return ConfidenceResult(
        confidence=round(confidence, 2),
        analyses_present=present,
        analyses_expected=expected,
        nonempty_categories=nonempty,
        details={
            "presence_ratio": round(presence_ratio, 4),
            "nonempty_ratio": round(nonempty_ratio, 4),
            "present_keys": list(present_keys),
            "finding_counts": dict(finding_counts),
        },
    )

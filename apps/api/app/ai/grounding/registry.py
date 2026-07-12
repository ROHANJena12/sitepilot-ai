"""Resolve GroundingValidator instances by output schema type."""

from __future__ import annotations

from typing import TypeVar

from app.ai.exceptions import GenerationNotImplemented
from app.ai.grounding.base import GroundingValidator
from app.ai.grounding.business import BusinessSummaryGroundingValidator
from app.ai.grounding.executive import ExecutiveSummaryGroundingValidator
from app.ai.grounding.finding import FindingGroundingValidator
from app.ai.grounding.quick_win import QuickWinGroundingValidator
from app.ai.grounding.recommendation import RecommendationGroundingValidator
from app.ai.schemas import (
    BusinessSummary,
    ExecutiveSummary,
    FindingExplanation,
    QuickWinExplanation,
    RecommendationExplanation,
)

T = TypeVar("T")

_VALIDATORS: dict[type[object], GroundingValidator[object]] = {
    FindingExplanation: FindingGroundingValidator(),  # type: ignore[dict-item]
    RecommendationExplanation: RecommendationGroundingValidator(),  # type: ignore[dict-item]
    ExecutiveSummary: ExecutiveSummaryGroundingValidator(),  # type: ignore[dict-item]
    BusinessSummary: BusinessSummaryGroundingValidator(),  # type: ignore[dict-item]
    QuickWinExplanation: QuickWinGroundingValidator(),  # type: ignore[dict-item]
}


def get_grounding_validator(output_type: type[T]) -> GroundingValidator[T]:
    validator = _VALIDATORS.get(output_type)  # type: ignore[arg-type]
    if validator is None:
        raise GenerationNotImplemented(
            f"No grounding validator registered for {output_type!r}."
        )
    return validator  # type: ignore[return-value]

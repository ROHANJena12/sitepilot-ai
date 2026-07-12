"""Recommendation AI use cases."""

from app.application.ai.recommendations.generate_quick_win import (
    GenerateQuickWinExplanationResult,
    GenerateQuickWinExplanationUseCase,
)
from app.application.ai.recommendations.generate_recommendation_explanation import (
    GenerateRecommendationExplanationResult,
    GenerateRecommendationExplanationUseCase,
)

__all__ = [
    "GenerateQuickWinExplanationResult",
    "GenerateQuickWinExplanationUseCase",
    "GenerateRecommendationExplanationResult",
    "GenerateRecommendationExplanationUseCase",
]

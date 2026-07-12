"""AI explanation application use cases (orchestration only)."""

from app.application.ai.exceptions import (
    AIApplicationError,
    AIFeatureUnavailableError,
    FindingNotFoundError,
    RecommendationNotFoundError,
)
from app.application.ai.findings import (
    GenerateFindingExplanationResult,
    GenerateFindingExplanationUseCase,
)
from app.application.ai.recommendations import (
    GenerateQuickWinExplanationResult,
    GenerateQuickWinExplanationUseCase,
    GenerateRecommendationExplanationResult,
    GenerateRecommendationExplanationUseCase,
)
from app.application.ai.reports import (
    GenerateBusinessSummaryResult,
    GenerateBusinessSummaryUseCase,
    GenerateExecutiveSummaryResult,
    GenerateExecutiveSummaryUseCase,
)

__all__ = [
    "AIApplicationError",
    "AIFeatureUnavailableError",
    "FindingNotFoundError",
    "GenerateBusinessSummaryResult",
    "GenerateBusinessSummaryUseCase",
    "GenerateExecutiveSummaryResult",
    "GenerateExecutiveSummaryUseCase",
    "GenerateFindingExplanationResult",
    "GenerateFindingExplanationUseCase",
    "GenerateQuickWinExplanationResult",
    "GenerateQuickWinExplanationUseCase",
    "GenerateRecommendationExplanationResult",
    "GenerateRecommendationExplanationUseCase",
    "RecommendationNotFoundError",
]

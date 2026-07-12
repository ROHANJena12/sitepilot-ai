"""Regenerate recommendation explanation — append-only versioning."""

from __future__ import annotations

from dataclasses import dataclass
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.ai.response import AIResponse
from app.ai.schemas import RecommendationExplanation
from app.ai.service import AIService
from app.application.ai.recommendations.generate_recommendation_explanation import (
    GenerateRecommendationExplanationUseCase,
)


@dataclass(frozen=True, slots=True)
class RegenerateRecommendationExplanationResult:
    response: AIResponse[RecommendationExplanation]


class RegenerateRecommendationExplanationUseCase:
    def __init__(self, session: AsyncSession, ai_service: AIService) -> None:
        self._generate = GenerateRecommendationExplanationUseCase(session, ai_service)

    async def execute(
        self, recommendation_id: UUID
    ) -> RegenerateRecommendationExplanationResult:
        result = await self._generate.execute(recommendation_id)
        return RegenerateRecommendationExplanationResult(response=result.response)

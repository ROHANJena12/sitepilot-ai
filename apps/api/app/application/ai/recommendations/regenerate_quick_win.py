"""Regenerate quick-win explanation — append-only versioning."""

from __future__ import annotations

from dataclasses import dataclass
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.ai.response import AIResponse
from app.ai.schemas import QuickWinExplanation
from app.ai.service import AIService
from app.application.ai.recommendations.generate_quick_win import (
    GenerateQuickWinExplanationUseCase,
)


@dataclass(frozen=True, slots=True)
class RegenerateQuickWinExplanationResult:
    response: AIResponse[QuickWinExplanation]


class RegenerateQuickWinExplanationUseCase:
    def __init__(self, session: AsyncSession, ai_service: AIService) -> None:
        self._generate = GenerateQuickWinExplanationUseCase(session, ai_service)

    async def execute(
        self, recommendation_id: UUID
    ) -> RegenerateQuickWinExplanationResult:
        result = await self._generate.execute(recommendation_id)
        return RegenerateQuickWinExplanationResult(response=result.response)

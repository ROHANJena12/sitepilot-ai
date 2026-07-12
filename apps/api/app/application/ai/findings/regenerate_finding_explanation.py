"""Regenerate finding explanation — same flow as generate (new immutable version)."""

from __future__ import annotations

from dataclasses import dataclass
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.ai.response import AIResponse
from app.ai.schemas import FindingExplanation
from app.ai.service import AIService
from app.application.ai.findings.generate_finding_explanation import (
    GenerateFindingExplanationUseCase,
)


@dataclass(frozen=True, slots=True)
class RegenerateFindingExplanationResult:
    response: AIResponse[FindingExplanation]


class RegenerateFindingExplanationUseCase:
    """Re-run finding explanation; persistence creates version+1 or reuses hash."""

    def __init__(self, session: AsyncSession, ai_service: AIService) -> None:
        self._generate = GenerateFindingExplanationUseCase(session, ai_service)

    async def execute(self, finding_id: UUID) -> RegenerateFindingExplanationResult:
        result = await self._generate.execute(finding_id)
        return RegenerateFindingExplanationResult(response=result.response)

"""Regenerate executive summary — append-only versioning."""

from __future__ import annotations

from dataclasses import dataclass
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.ai.response import AIResponse
from app.ai.schemas import ExecutiveSummary
from app.ai.service import AIService
from app.application.ai.reports.generate_executive_summary import (
    GenerateExecutiveSummaryUseCase,
)


@dataclass(frozen=True, slots=True)
class RegenerateExecutiveSummaryResult:
    response: AIResponse[ExecutiveSummary]


class RegenerateExecutiveSummaryUseCase:
    def __init__(self, session: AsyncSession, ai_service: AIService) -> None:
        self._generate = GenerateExecutiveSummaryUseCase(session, ai_service)

    async def execute(self, audit_id: UUID) -> RegenerateExecutiveSummaryResult:
        result = await self._generate.execute(audit_id)
        return RegenerateExecutiveSummaryResult(response=result.response)

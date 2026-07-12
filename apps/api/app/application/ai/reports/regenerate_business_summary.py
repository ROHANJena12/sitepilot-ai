"""Regenerate business summary — append-only versioning."""

from __future__ import annotations

from dataclasses import dataclass
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.ai.response import AIResponse
from app.ai.schemas import BusinessSummary
from app.ai.service import AIService
from app.application.ai.reports.generate_business_summary import (
    GenerateBusinessSummaryUseCase,
)


@dataclass(frozen=True, slots=True)
class RegenerateBusinessSummaryResult:
    response: AIResponse[BusinessSummary]


class RegenerateBusinessSummaryUseCase:
    def __init__(self, session: AsyncSession, ai_service: AIService) -> None:
        self._generate = GenerateBusinessSummaryUseCase(session, ai_service)

    async def execute(self, audit_id: UUID) -> RegenerateBusinessSummaryResult:
        result = await self._generate.execute(audit_id)
        return RegenerateBusinessSummaryResult(response=result.response)

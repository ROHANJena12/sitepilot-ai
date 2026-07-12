"""GenerateBusinessSummaryUseCase — report DTO → mapper → AIService."""

from __future__ import annotations

from dataclasses import dataclass
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.ai.entity_types import AIEntityType
from app.ai.features import AIFeature
from app.ai.mappers import report_to_business_ai_context
from app.ai.response import AIResponse
from app.ai.schemas import BusinessSummary
from app.ai.service import AIService
from app.application.ai.persist import AIGenerationPersister
from app.application.get_report import GetAuditReportUseCase


@dataclass(frozen=True, slots=True)
class GenerateBusinessSummaryResult:
    response: AIResponse[BusinessSummary]


class GenerateBusinessSummaryUseCase:
    def __init__(self, session: AsyncSession, ai_service: AIService) -> None:
        self._reports = GetAuditReportUseCase(session)
        self._ai = ai_service
        self._persist = AIGenerationPersister(session)

    async def execute(self, audit_id: UUID) -> GenerateBusinessSummaryResult:
        report = (await self._reports.execute(audit_id)).report
        context = report_to_business_ai_context(report)
        response = await self._ai.generate_business_summary(context)
        await self._persist.persist(
            response,
            feature=AIFeature.BUSINESS_SUMMARY,
            entity_type=AIEntityType.BUSINESS_SUMMARY,
            entity_id=str(report.audit_id),
            audit_id=report.audit_id,
            report_hash=report.report_hash,
        )
        return GenerateBusinessSummaryResult(response=response)

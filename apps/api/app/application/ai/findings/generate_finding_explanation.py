"""GenerateFindingExplanationUseCase — finding row → report DTO → mapper → AIService."""

from __future__ import annotations

from dataclasses import dataclass
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.ai.entity_types import AIEntityType
from app.ai.features import AIFeature
from app.ai.mappers import finding_to_ai_context
from app.ai.response import AIResponse
from app.ai.schemas import FindingExplanation
from app.ai.service import AIService
from app.application.ai.adapters import (
    finding_dto_to_snapshot,
    finding_from_report,
    website_from_report,
)
from app.application.ai.exceptions import FindingNotFoundError
from app.application.ai.persist import AIGenerationPersister
from app.application.get_report import GetAuditReportUseCase
from app.repositories.finding import FindingRepository


@dataclass(frozen=True, slots=True)
class GenerateFindingExplanationResult:
    response: AIResponse[FindingExplanation]


class GenerateFindingExplanationUseCase:
    def __init__(self, session: AsyncSession, ai_service: AIService) -> None:
        self._session = session
        self._findings = FindingRepository(session)
        self._reports = GetAuditReportUseCase(session)
        self._ai = ai_service
        self._persist = AIGenerationPersister(session)

    async def execute(self, finding_id: UUID) -> GenerateFindingExplanationResult:
        row = await self._findings.get_by_id(finding_id)
        if row is None:
            raise FindingNotFoundError(
                "Finding not found or has been deleted.",
            )

        report = (await self._reports.execute(row.audit_run_id)).report
        dto = finding_from_report(report, row.finding_id)
        if dto is None:
            raise FindingNotFoundError(
                "Finding is not present in the assembled report.",
            )

        context = finding_to_ai_context(
            finding_dto_to_snapshot(dto),
            website=website_from_report(report),
            health_score=report.health.overall_score,
            audit_id=report.audit_id,
            report_hash=report.report_hash,
        )
        response = await self._ai.explain_finding(context)
        await self._persist.persist(
            response,
            feature=AIFeature.FINDING,
            entity_type=AIEntityType.FINDING,
            entity_id=dto.id,
            audit_id=report.audit_id,
            report_hash=report.report_hash,
        )
        return GenerateFindingExplanationResult(response=response)

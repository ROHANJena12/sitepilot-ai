"""GenerateRecommendationExplanationUseCase — rec row → report → mapper → AIService."""

from __future__ import annotations

from dataclasses import dataclass
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.ai.entity_types import AIEntityType
from app.ai.features import AIFeature
from app.ai.mappers import recommendation_to_ai_context
from app.ai.response import AIResponse
from app.ai.schemas import RecommendationExplanation
from app.ai.service import AIService
from app.application.ai.adapters import (
    recommendation_dto_to_snapshot,
    recommendation_from_report,
    related_findings_for,
    website_from_report,
)
from app.application.ai.exceptions import RecommendationNotFoundError
from app.application.ai.persist import AIGenerationPersister
from app.application.get_report import GetAuditReportUseCase
from app.repositories.recommendation import RecommendationRepository


@dataclass(frozen=True, slots=True)
class GenerateRecommendationExplanationResult:
    response: AIResponse[RecommendationExplanation]


class GenerateRecommendationExplanationUseCase:
    def __init__(self, session: AsyncSession, ai_service: AIService) -> None:
        self._recommendations = RecommendationRepository(session)
        self._reports = GetAuditReportUseCase(session)
        self._ai = ai_service
        self._persist = AIGenerationPersister(session)

    async def execute(
        self, recommendation_id: UUID
    ) -> GenerateRecommendationExplanationResult:
        row = await self._recommendations.get_by_id(recommendation_id)
        if row is None:
            raise RecommendationNotFoundError(
                "Recommendation not found or has been deleted.",
            )

        report = (await self._reports.execute(row.audit_run_id)).report
        dto = recommendation_from_report(report, row.recommendation_id)
        if dto is None:
            raise RecommendationNotFoundError(
                "Recommendation is not present in the assembled report.",
            )

        snapshot = recommendation_dto_to_snapshot(dto)
        context = recommendation_to_ai_context(
            snapshot,
            related_findings=related_findings_for(
                report, snapshot.affected_findings
            ),
            website=website_from_report(report),
            health_score=report.health.overall_score,
            audit_id=report.audit_id,
            report_hash=report.report_hash,
        )
        response = await self._ai.explain_recommendation(context)
        await self._persist.persist(
            response,
            feature=AIFeature.RECOMMENDATION,
            entity_type=AIEntityType.RECOMMENDATION,
            entity_id=dto.recommendation_id,
            audit_id=report.audit_id,
            report_hash=report.report_hash,
        )
        return GenerateRecommendationExplanationResult(response=response)

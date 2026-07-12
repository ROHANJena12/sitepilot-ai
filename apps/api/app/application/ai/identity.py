"""Resolve AI persistence keys from API path IDs (row UUIDs / audit UUID)."""

from __future__ import annotations

from dataclasses import dataclass
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.ai.entity_types import AIEntityType
from app.ai.features import AIFeature
from app.application.ai.adapters import (
    finding_from_report,
    recommendation_from_report,
)
from app.application.ai.exceptions import (
    AIFeatureUnavailableError,
    FindingNotFoundError,
    RecommendationNotFoundError,
)
from app.application.get_report import GetAuditReportUseCase
from app.repositories.finding import FindingRepository
from app.repositories.recommendation import RecommendationRepository


@dataclass(frozen=True, slots=True)
class AIGenerationKey:
    """Identity used for ai_generations lookups (matches Sprint 24 persistence)."""

    feature: AIFeature
    entity_type: AIEntityType
    entity_id: str
    audit_id: UUID
    report_hash: str | None


class AIGenerationKeyResolver:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session
        self._reports = GetAuditReportUseCase(session)
        self._findings = FindingRepository(session)
        self._recommendations = RecommendationRepository(session)

    async def for_finding(self, finding_row_id: UUID) -> AIGenerationKey:
        row = await self._findings.get_by_id(finding_row_id)
        if row is None:
            raise FindingNotFoundError("Finding not found or has been deleted.")
        report = (await self._reports.execute(row.audit_run_id)).report
        dto = finding_from_report(report, row.finding_id)
        if dto is None:
            raise FindingNotFoundError(
                "Finding is not present in the assembled report.",
            )
        return AIGenerationKey(
            feature=AIFeature.FINDING,
            entity_type=AIEntityType.FINDING,
            entity_id=dto.id,
            audit_id=report.audit_id,
            report_hash=report.report_hash,
        )

    async def for_recommendation(self, recommendation_row_id: UUID) -> AIGenerationKey:
        row = await self._recommendations.get_by_id(recommendation_row_id)
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
        return AIGenerationKey(
            feature=AIFeature.RECOMMENDATION,
            entity_type=AIEntityType.RECOMMENDATION,
            entity_id=dto.recommendation_id,
            audit_id=report.audit_id,
            report_hash=report.report_hash,
        )

    async def for_quick_win(self, recommendation_row_id: UUID) -> AIGenerationKey:
        row = await self._recommendations.get_by_id(recommendation_row_id)
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
        if not dto.is_quick_win:
            raise AIFeatureUnavailableError(
                "Quick Win history is only available for recommendations "
                "marked as quick wins by the Recommendation Engine.",
            )
        return AIGenerationKey(
            feature=AIFeature.QUICK_WIN,
            entity_type=AIEntityType.QUICK_WIN,
            entity_id=dto.recommendation_id,
            audit_id=report.audit_id,
            report_hash=report.report_hash,
        )

    async def for_executive_summary(self, audit_id: UUID) -> AIGenerationKey:
        report = (await self._reports.execute(audit_id)).report
        return AIGenerationKey(
            feature=AIFeature.EXECUTIVE_SUMMARY,
            entity_type=AIEntityType.EXECUTIVE_SUMMARY,
            entity_id=str(report.audit_id),
            audit_id=report.audit_id,
            report_hash=report.report_hash,
        )

    async def for_business_summary(self, audit_id: UUID) -> AIGenerationKey:
        report = (await self._reports.execute(audit_id)).report
        return AIGenerationKey(
            feature=AIFeature.BUSINESS_SUMMARY,
            entity_type=AIEntityType.BUSINESS_SUMMARY,
            entity_id=str(report.audit_id),
            audit_id=report.audit_id,
            report_hash=report.report_hash,
        )

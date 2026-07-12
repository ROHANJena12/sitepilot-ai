"""Start Audit Run use-case — orchestration only (no engines)."""

from __future__ import annotations

from dataclasses import dataclass
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.domain.audit_status import AuditStatus
from app.domain.exceptions import DomainValidationError
from app.models.audit_run import AuditRun
from app.repositories.audit import AuditRepository
from app.repositories.website import WebsiteRepository


@dataclass(frozen=True, slots=True)
class StartAuditResult:
    audit_run: AuditRun


class StartAuditUseCase:
    """
    Create an AuditRun in PENDING status for an existing Website.

    Does not enqueue workers or execute engines.
    """

    def __init__(self, session: AsyncSession) -> None:
        self._websites = WebsiteRepository(session)
        self._audits = AuditRepository(session)

    async def execute(self, website_id: UUID) -> StartAuditResult:
        website = await self._websites.get_by_id(website_id)
        if website is None:
            raise DomainValidationError(
                "Website not found or has been deleted.",
                code="WEBSITE_NOT_FOUND",
            )

        project = website.project
        audit = AuditRun(
            website_id=website.id,
            organization_id=project.organization_id,
            project_id=website.project_id,
            requested_url=website.original_url,
            canonical_url=website.canonical_url,
            status=AuditStatus.PENDING.value,
            progress_percent=0,
            current_engine=None,
            engine_versions={},
            pipeline_metadata={},
        )
        created = await self._audits.create(audit)
        return StartAuditResult(audit_run=created)

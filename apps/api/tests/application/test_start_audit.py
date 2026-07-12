"""StartAuditUseCase tests."""

from __future__ import annotations

from uuid import uuid4

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.application.start_audit import StartAuditUseCase
from app.domain.audit_status import AuditStatus
from app.domain.exceptions import DomainValidationError
from app.repositories.organization import OrganizationRepository
from app.repositories.project import ProjectRepository
from app.repositories.website import WebsiteRepository
from app.schemas.organization import OrganizationCreate
from app.schemas.project import ProjectCreate
from app.schemas.website import WebsiteCreate


async def _seed_website(session: AsyncSession):
    org = await OrganizationRepository(session).create(
        OrganizationCreate(name="UC Org", slug="uc-org")
    )
    project = await ProjectRepository(session).create(
        ProjectCreate(organization_id=org.id, name="UC Project", slug="uc-project")
    )
    website = await WebsiteRepository(session).create(
        WebsiteCreate(project_id=project.id, url="https://acme.test")
    )
    return org, project, website


@pytest.mark.asyncio
async def test_start_audit_creates_pending_run(db_session: AsyncSession) -> None:
    org, project, website = await _seed_website(db_session)

    result = await StartAuditUseCase(db_session).execute(website.id)
    audit = result.audit_run

    assert audit.status == AuditStatus.PENDING.value
    assert audit.website_id == website.id
    assert audit.organization_id == org.id
    assert audit.project_id == project.id
    assert audit.canonical_url == website.canonical_url
    assert audit.progress_percent == 0
    assert audit.health_score is None


@pytest.mark.asyncio
async def test_start_audit_rejects_missing_website(db_session: AsyncSession) -> None:
    with pytest.raises(DomainValidationError) as exc_info:
        await StartAuditUseCase(db_session).execute(uuid4())
    assert exc_info.value.code == "WEBSITE_NOT_FOUND"


@pytest.mark.asyncio
async def test_start_audit_rejects_soft_deleted_website(db_session: AsyncSession) -> None:
    _, _, website = await _seed_website(db_session)
    await WebsiteRepository(db_session).delete(website.id)

    with pytest.raises(DomainValidationError) as exc_info:
        await StartAuditUseCase(db_session).execute(website.id)
    assert exc_info.value.code == "WEBSITE_NOT_FOUND"

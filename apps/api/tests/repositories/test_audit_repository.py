"""AuditRun repository tests."""

from __future__ import annotations

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.domain.audit_status import AuditStatus
from app.models.audit_run import AuditRun
from app.repositories.audit import AuditRepository
from app.repositories.organization import OrganizationRepository
from app.repositories.project import ProjectRepository
from app.repositories.website import WebsiteRepository
from app.schemas.organization import OrganizationCreate
from app.schemas.project import ProjectCreate
from app.schemas.website import WebsiteCreate


async def _seed_website(session: AsyncSession):
    org = await OrganizationRepository(session).create(
        OrganizationCreate(name="Audit Org", slug="audit-org")
    )
    project = await ProjectRepository(session).create(
        ProjectCreate(organization_id=org.id, name="Audit Project", slug="audit-project")
    )
    website = await WebsiteRepository(session).create(
        WebsiteCreate(project_id=project.id, url="https://example.com")
    )
    return org, project, website


def _new_audit(org_id, project_id, website) -> AuditRun:
    return AuditRun(
        website_id=website.id,
        organization_id=org_id,
        project_id=project_id,
        requested_url=website.original_url,
        canonical_url=website.canonical_url,
        status=AuditStatus.PENDING.value,
        progress_percent=0,
        engine_versions={},
        pipeline_metadata={},
    )


@pytest.mark.asyncio
async def test_create_get_list_by_website(db_session: AsyncSession) -> None:
    org, project, website = await _seed_website(db_session)
    audits = AuditRepository(db_session)

    created = await audits.create(_new_audit(org.id, project.id, website))
    assert created.status == AuditStatus.PENDING.value
    assert created.progress_percent == 0
    assert created.health_score is None

    fetched = await audits.get_by_id(created.id)
    assert fetched is not None
    assert fetched.id == created.id

    listed = await audits.list_by_website(website.id)
    assert len(listed) == 1
    assert listed[0].id == created.id


@pytest.mark.asyncio
async def test_update_progress_and_status(db_session: AsyncSession) -> None:
    org, project, website = await _seed_website(db_session)
    audits = AuditRepository(db_session)
    created = await audits.create(_new_audit(org.id, project.id, website))

    updated = await audits.update_progress(
        created.id,
        progress_percent=40,
        current_engine="seo_intelligence",
        status=AuditStatus.ANALYZING,
    )
    assert updated is not None
    assert updated.progress_percent == 40
    assert updated.current_engine == "seo_intelligence"
    assert updated.status == AuditStatus.ANALYZING.value
    assert updated.started_at is not None

    statused = await audits.update_status(created.id, AuditStatus.SCORING)
    assert statused is not None
    assert statused.status == AuditStatus.SCORING.value


@pytest.mark.asyncio
async def test_mark_completed(db_session: AsyncSession) -> None:
    org, project, website = await _seed_website(db_session)
    audits = AuditRepository(db_session)
    created = await audits.create(_new_audit(org.id, project.id, website))
    await audits.update_progress(created.id, progress_percent=10, status=AuditStatus.ANALYZING)

    completed = await audits.mark_completed(
        created.id,
        health_score=82,
        seo_score=80,
        performance_score=75,
        security_score=90,
        accessibility_score=70,
    )
    assert completed is not None
    assert completed.status == AuditStatus.COMPLETE.value
    assert completed.progress_percent == 100
    assert completed.health_score == 82
    assert completed.completed_at is not None
    assert completed.duration_ms is not None


@pytest.mark.asyncio
async def test_mark_failed(db_session: AsyncSession) -> None:
    org, project, website = await _seed_website(db_session)
    audits = AuditRepository(db_session)
    created = await audits.create(_new_audit(org.id, project.id, website))

    failed = await audits.mark_failed(
        created.id,
        failure_code="PIPELINE_ERROR",
        failure_message="Engine orchestration failed.",
    )
    assert failed is not None
    assert failed.status == AuditStatus.FAILED.value
    assert failed.failure_code == "PIPELINE_ERROR"
    assert failed.failure_message == "Engine orchestration failed."
    assert failed.completed_at is not None

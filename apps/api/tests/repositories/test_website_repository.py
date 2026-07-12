"""Website repository tests."""

from __future__ import annotations

import pytest
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.repositories.organization import OrganizationRepository
from app.repositories.project import ProjectRepository
from app.repositories.website import WebsiteRepository
from app.schemas.organization import OrganizationCreate
from app.schemas.project import ProjectCreate
from app.schemas.website import WebsiteCreate, WebsiteUpdate


async def _seed_project(session: AsyncSession):
    org = await OrganizationRepository(session).create(
        OrganizationCreate(name="Seed Org", slug="seed-org")
    )
    project = await ProjectRepository(session).create(
        ProjectCreate(organization_id=org.id, name="Seed Project", slug="seed-project")
    )
    return org, project


@pytest.mark.asyncio
async def test_website_create_list_update_soft_delete(db_session: AsyncSession) -> None:
    _, project = await _seed_project(db_session)
    websites = WebsiteRepository(db_session)

    created = await websites.create(
        WebsiteCreate(project_id=project.id, url="https://www.Contoso.com/app/")
    )
    assert created.host == "www.contoso.com"
    assert created.canonical_url == "https://www.contoso.com/app"
    assert created.is_https is True

    listed = await websites.list_by_project(project.id)
    assert len(listed) == 1

    updated = await websites.update(
        created.id,
        WebsiteUpdate(url="https://contoso.com", title_last_seen="Contoso"),
    )
    assert updated is not None
    assert updated.canonical_url == "https://contoso.com"
    assert updated.title_last_seen == "Contoso"

    deleted = await websites.delete(created.id)
    assert deleted is not None
    assert deleted.deleted_at is not None
    assert await websites.list_by_project(project.id) == []


@pytest.mark.asyncio
async def test_website_duplicate_canonical_rejected(db_session: AsyncSession) -> None:
    _, project = await _seed_project(db_session)
    websites = WebsiteRepository(db_session)

    await websites.create(WebsiteCreate(project_id=project.id, url="https://example.com"))
    await db_session.flush()

    with pytest.raises(IntegrityError):
        await websites.create(WebsiteCreate(project_id=project.id, url="https://example.com/"))
        await db_session.flush()
    await db_session.rollback()

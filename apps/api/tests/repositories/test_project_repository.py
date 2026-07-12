"""Project repository tests."""

from __future__ import annotations

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.repositories.organization import OrganizationRepository
from app.repositories.project import ProjectRepository
from app.schemas.organization import OrganizationCreate
from app.schemas.project import ProjectCreate, ProjectUpdate


@pytest.mark.asyncio
async def test_project_create_list_update_soft_delete(db_session: AsyncSession) -> None:
    orgs = OrganizationRepository(db_session)
    projects = ProjectRepository(db_session)

    org = await orgs.create(OrganizationCreate(name="Acme", slug="acme"))
    created = await projects.create(
        ProjectCreate(
            organization_id=org.id,
            name="Client Contoso",
            slug="client-contoso",
            description="Marketing sites",
        )
    )
    assert created.organization_id == org.id
    assert created.slug == "client-contoso"

    listed = await projects.list_by_organization(org.id)
    assert len(listed) == 1
    assert listed[0].id == created.id

    updated = await projects.update(created.id, ProjectUpdate(status="archived"))
    assert updated is not None
    assert updated.status == "archived"

    deleted = await projects.delete(created.id)
    assert deleted is not None
    assert deleted.deleted_at is not None
    assert await projects.get_by_id(created.id) is None
    assert await projects.list_by_organization(org.id) == []

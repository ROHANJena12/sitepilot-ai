"""Organization repository tests."""

from __future__ import annotations

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.repositories.organization import OrganizationRepository
from app.schemas.organization import OrganizationCreate, OrganizationUpdate


@pytest.mark.asyncio
async def test_organization_create_get_update_soft_delete(db_session: AsyncSession) -> None:
    repo = OrganizationRepository(db_session)

    created = await repo.create(
        OrganizationCreate(name="Northwind", slug="Northwind-Agency", plan_tier="pro")
    )
    assert created.id is not None
    assert created.slug == "northwind-agency"
    assert created.plan_tier == "pro"

    fetched = await repo.get_by_id(created.id)
    assert fetched is not None
    assert fetched.name == "Northwind"

    by_slug = await repo.get_by_slug("northwind-agency")
    assert by_slug is not None
    assert by_slug.id == created.id

    updated = await repo.update(created.id, OrganizationUpdate(name="Northwind Labs"))
    assert updated is not None
    assert updated.name == "Northwind Labs"

    deleted = await repo.delete(created.id)
    assert deleted is not None
    assert deleted.deleted_at is not None
    assert await repo.get_by_id(created.id) is None
    assert await repo.get_by_slug("northwind-agency") is None


@pytest.mark.asyncio
async def test_organization_list(db_session: AsyncSession) -> None:
    repo = OrganizationRepository(db_session)
    await repo.create(OrganizationCreate(name="A", slug="org-a"))
    await repo.create(OrganizationCreate(name="B", slug="org-b"))

    rows = await repo.list(limit=10)
    assert len(rows) >= 2

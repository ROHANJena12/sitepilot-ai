"""Organization repository — persistence only."""

from __future__ import annotations

from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.organization import Organization
from app.repositories.base import get_active_by_id, not_deleted, soft_delete
from app.schemas.organization import OrganizationCreate, OrganizationUpdate


class OrganizationRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def create(self, data: OrganizationCreate) -> Organization:
        org = Organization(
            name=data.name,
            slug=data.slug,
            plan_tier=data.plan_tier,
            status=data.status,
            billing_email=data.billing_email,
            settings=data.settings,
        )
        self._session.add(org)
        await self._session.flush()
        await self._session.refresh(org)
        return org

    async def get_by_id(self, organization_id: UUID) -> Organization | None:
        return await get_active_by_id(self._session, Organization, organization_id)

    async def get_by_slug(self, slug: str) -> Organization | None:
        stmt = not_deleted(Organization).where(Organization.slug == slug)
        result = await self._session.execute(stmt)
        return result.scalar_one_or_none()

    async def list(self, *, limit: int = 50, offset: int = 0) -> list[Organization]:
        stmt = (
            not_deleted(Organization)
            .order_by(Organization.created_at.desc())
            .limit(limit)
            .offset(offset)
        )
        result = await self._session.execute(stmt)
        return list(result.scalars().all())

    async def update(
        self,
        organization_id: UUID,
        data: OrganizationUpdate,
    ) -> Organization | None:
        org = await self.get_by_id(organization_id)
        if org is None:
            return None

        payload = data.model_dump(exclude_unset=True)
        for key, value in payload.items():
            setattr(org, key, value)

        self._session.add(org)
        await self._session.flush()
        await self._session.refresh(org)
        return org

    async def delete(self, organization_id: UUID) -> Organization | None:
        org = await self.get_by_id(organization_id)
        if org is None:
            return None
        return await soft_delete(self._session, org)

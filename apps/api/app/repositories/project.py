"""Project repository — persistence only."""

from __future__ import annotations

from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.models.project import Project
from app.repositories.base import get_active_by_id, not_deleted, soft_delete
from app.schemas.project import ProjectCreate, ProjectUpdate


class ProjectRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def create(self, data: ProjectCreate) -> Project:
        project = Project(
            organization_id=data.organization_id,
            name=data.name,
            slug=data.slug,
            description=data.description,
            status=data.status,
            created_by_user_id=data.created_by_user_id,
        )
        self._session.add(project)
        await self._session.flush()
        await self._session.refresh(project)
        return project

    async def get_by_id(self, project_id: UUID) -> Project | None:
        return await get_active_by_id(self._session, Project, project_id)

    async def get_by_org_slug(
        self, organization_id: UUID, slug: str
    ) -> Project | None:
        stmt = (
            not_deleted(Project)
            .where(Project.organization_id == organization_id)
            .where(Project.slug == slug)
        )
        result = await self._session.execute(stmt)
        return result.scalar_one_or_none()

    async def list_by_organization(
        self,
        organization_id: UUID,
        *,
        limit: int = 50,
        offset: int = 0,
    ) -> list[Project]:
        stmt = (
            not_deleted(Project)
            .where(Project.organization_id == organization_id)
            .order_by(Project.created_at.desc())
            .limit(limit)
            .offset(offset)
        )
        result = await self._session.execute(stmt)
        return list(result.scalars().all())

    async def update(self, project_id: UUID, data: ProjectUpdate) -> Project | None:
        project = await self.get_by_id(project_id)
        if project is None:
            return None

        payload = data.model_dump(exclude_unset=True)
        for key, value in payload.items():
            setattr(project, key, value)

        self._session.add(project)
        await self._session.flush()
        await self._session.refresh(project)
        return project

    async def delete(self, project_id: UUID) -> Project | None:
        project = await self.get_by_id(project_id)
        if project is None:
            return None
        return await soft_delete(self._session, project)

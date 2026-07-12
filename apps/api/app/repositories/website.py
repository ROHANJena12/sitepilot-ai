"""Website repository — persistence only."""

from __future__ import annotations

from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.models.website import Website
from app.repositories.base import get_active_by_id, not_deleted, soft_delete
from app.schemas.website import WebsiteCreate, WebsiteUpdate


class WebsiteRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def create(self, data: WebsiteCreate) -> Website:
        parsed = data.parsed
        website = Website(
            project_id=data.project_id,
            canonical_url=parsed.canonical_url,
            original_url=parsed.original_url,
            host=parsed.host,
            is_https=parsed.is_https,
            technology_stack=data.technology_stack,
            language=data.language,
            country=data.country,
            industry=data.industry,
            favicon_url=data.favicon_url,
            title_last_seen=data.title_last_seen,
        )
        self._session.add(website)
        await self._session.flush()
        await self._session.refresh(website)
        return website

    async def get_by_id(self, website_id: UUID) -> Website | None:
        return await get_active_by_id(self._session, Website, website_id)

    async def get_by_canonical(
        self,
        project_id: UUID,
        canonical_url: str,
    ) -> Website | None:
        stmt = (
            not_deleted(Website)
            .where(Website.project_id == project_id)
            .where(Website.canonical_url == canonical_url)
        )
        result = await self._session.execute(stmt)
        return result.scalar_one_or_none()

    async def list_by_project(
        self,
        project_id: UUID,
        *,
        limit: int = 50,
        offset: int = 0,
    ) -> list[Website]:
        stmt = (
            not_deleted(Website)
            .where(Website.project_id == project_id)
            .order_by(Website.created_at.desc())
            .limit(limit)
            .offset(offset)
        )
        result = await self._session.execute(stmt)
        return list(result.scalars().all())

    async def update(self, website_id: UUID, data: WebsiteUpdate) -> Website | None:
        website = await self.get_by_id(website_id)
        if website is None:
            return None

        payload = data.model_dump(exclude_unset=True, exclude={"url"})
        for key, value in payload.items():
            setattr(website, key, value)

        if data.parsed is not None:
            website.canonical_url = data.parsed.canonical_url
            website.original_url = data.parsed.original_url
            website.host = data.parsed.host
            website.is_https = data.parsed.is_https

        self._session.add(website)
        await self._session.flush()
        await self._session.refresh(website)
        return website

    async def delete(self, website_id: UUID) -> Website | None:
        website = await self.get_by_id(website_id)
        if website is None:
            return None
        return await soft_delete(self._session, website)

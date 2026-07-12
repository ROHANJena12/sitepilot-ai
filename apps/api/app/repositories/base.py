"""Repository helpers — soft-delete aware query filters."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import TypeVar
from uuid import UUID

from sqlalchemy import Select, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import DeclarativeBase

ModelT = TypeVar("ModelT", bound=DeclarativeBase)


def utcnow() -> datetime:
    return datetime.now(UTC)


def not_deleted(model: type[ModelT]) -> Select[tuple[ModelT]]:
    return select(model).where(model.deleted_at.is_(None))  # type: ignore[attr-defined]


async def soft_delete(session: AsyncSession, entity: ModelT) -> ModelT:
    entity.deleted_at = utcnow()  # type: ignore[attr-defined]
    session.add(entity)
    await session.flush()
    return entity


async def get_active_by_id(
    session: AsyncSession,
    model: type[ModelT],
    entity_id: UUID,
) -> ModelT | None:
    stmt = not_deleted(model).where(model.id == entity_id)  # type: ignore[attr-defined]
    result = await session.execute(stmt)
    return result.scalar_one_or_none()

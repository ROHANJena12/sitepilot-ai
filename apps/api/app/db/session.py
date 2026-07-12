"""Async session helpers."""

from __future__ import annotations

from collections.abc import AsyncIterator

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker


async def get_session(
    session_factory: async_sessionmaker[AsyncSession],
) -> AsyncIterator[AsyncSession]:
    """Yield a request-scoped async session."""
    async with session_factory() as session:
        try:
            yield session
        except Exception:
            await session.rollback()
            raise

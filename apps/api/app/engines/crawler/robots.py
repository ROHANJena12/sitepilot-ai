"""robots.txt foundation — interfaces only (implementation deferred).

Sprint 6 does **not** enforce robots.txt. These stubs exist so Sprint 7+ can
wire fetch/parse/cache without changing the crawler call sites.
"""

from __future__ import annotations

from typing import Any, Protocol


class RobotsCache(Protocol):
    """Cache port for robots.txt documents (deferred)."""

    async def get(self, origin: str) -> str | None:
        """Return cached robots body for origin, if any."""
        ...

    async def set(self, origin: str, body: str, *, ttl_seconds: int) -> None:
        """Store robots body for origin."""
        ...


async def fetch(origin: str, *, client: Any = None, timeout: float = 5.0) -> str:
    """
    Fetch ``{origin}/robots.txt``.

    Deferred: raises ``NotImplementedError``.
    """
    raise NotImplementedError("robots.fetch is deferred past Sprint 6")


def parse(body: str, *, user_agent: str) -> dict[str, Any]:
    """
    Parse robots.txt into a structured policy object.

    Deferred: raises ``NotImplementedError``.
    """
    raise NotImplementedError("robots.parse is deferred past Sprint 6")


def cache(origin: str, body: str, *, store: RobotsCache, ttl_seconds: int = 3600) -> None:
    """
    Synchronously schedule cache write for robots.txt (interface only).

    Deferred: raises ``NotImplementedError``.
    """
    raise NotImplementedError("robots.cache is deferred past Sprint 6")

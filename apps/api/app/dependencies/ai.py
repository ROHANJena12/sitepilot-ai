"""AIService FastAPI dependency."""

from __future__ import annotations

from functools import lru_cache

from app.ai.service import AIService


@lru_cache(maxsize=1)
def get_ai_service() -> AIService:
    """
    Process-local AIService singleton.

    Override in tests via ``app.dependency_overrides[get_ai_service]``.
    """
    return AIService()

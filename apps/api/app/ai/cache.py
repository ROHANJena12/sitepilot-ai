"""AI cache abstraction (no Redis yet)."""

from __future__ import annotations

import hashlib
import json
from abc import ABC, abstractmethod
from collections.abc import Mapping
from typing import Protocol, runtime_checkable


@runtime_checkable
class SupportsModelDump(Protocol):
    def model_dump(self, *, mode: str = "python") -> dict[str, object]: ...


def build_cache_key(
    *,
    provider: str,
    model: str,
    schema_version: str,
    builder_version: int | str,
    prompt_version: str,
    report_hash: str,
    input_hash: str,
    locale: str = "en",
    entity_id: str = "",
    recommendation_id: str | None = None,
) -> str:
    """
    Deterministic cache key (single implementation — do not duplicate).

    SHA256(
      provider | model | schema_version | builder_version |
      prompt_version | locale | report_hash | entity_id | input_hash
    )

    ``entity_id`` is ``finding_id`` or ``recommendation_id`` by feature.
    ``recommendation_id`` remains accepted as a deprecated alias for ``entity_id``.
    """
    resolved_entity = entity_id.strip()
    if not resolved_entity and recommendation_id is not None:
        resolved_entity = recommendation_id.strip()
    payload = "|".join(
        [
            provider.strip().lower(),
            model.strip(),
            schema_version.strip(),
            str(builder_version).strip(),
            prompt_version.strip(),
            (locale or "en").strip().lower(),
            report_hash.strip(),
            resolved_entity,
            input_hash.strip(),
        ]
    )
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def hash_input_payload(payload: Mapping[str, object] | SupportsModelDump) -> str:
    """Stable SHA-256 for prompt-safe input material."""
    if isinstance(payload, SupportsModelDump):
        data: Mapping[str, object] = payload.model_dump(mode="json")
    else:
        data = payload
    canonical = json.dumps(dict(data), ensure_ascii=False, sort_keys=True, default=str)
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


class AICache(ABC):
    """
    Cache port for AI responses.

    Future RedisAICache must implement this without changing AIService call sites.
    """

    @abstractmethod
    async def get(self, key: str) -> object | None:
        ...

    @abstractmethod
    async def set(self, key: str, value: object, *, ttl_seconds: int | None = None) -> None:
        ...

    @abstractmethod
    async def delete(self, key: str) -> None:
        ...

    @abstractmethod
    async def clear(self) -> None:
        ...


class NullAICache(AICache):
    """No-op cache used when caching is disabled or Redis is not wired."""

    async def get(self, key: str) -> object | None:
        return None

    async def set(self, key: str, value: object, *, ttl_seconds: int | None = None) -> None:
        return None

    async def delete(self, key: str) -> None:
        return None

    async def clear(self) -> None:
        return None


class InMemoryAICache(AICache):
    """Process-local cache for tests and single-process development."""

    def __init__(self) -> None:
        self._store: dict[str, object] = {}

    async def get(self, key: str) -> object | None:
        return self._store.get(key)

    async def set(self, key: str, value: object, *, ttl_seconds: int | None = None) -> None:
        self._store[key] = value

    async def delete(self, key: str) -> None:
        self._store.pop(key, None)

    async def clear(self) -> None:
        self._store.clear()

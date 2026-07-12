"""QueueFactory — select InMemoryQueue or RedisQueue from settings."""

from __future__ import annotations

from typing import Any

from app.ai.jobs.identity import DEFAULT_WORKER_ID
from app.ai.jobs.queue import InMemoryQueue, QueuePort
from app.ai.jobs.redis_queue import RedisQueue
from app.core.config import Settings


def normalize_queue_backend(value: str | None) -> str:
    backend = (value or "inmemory").strip().lower()
    if backend in ("redis", "memory", "in-memory", "inmemory"):
        return "redis" if backend == "redis" else "inmemory"
    raise ValueError(
        f"Unsupported AI_QUEUE_BACKEND={value!r}; expected 'inmemory' or 'redis'."
    )


def create_redis_client(redis_url: str) -> Any:
    """Create a redis.asyncio client (lazy import so inmemory mode needs no Redis)."""
    from redis.asyncio import Redis

    return Redis.from_url(redis_url, decode_responses=True)


def create_job_queue(
    settings: Settings,
    *,
    redis_client: Any | None = None,
    worker_id: str | None = None,
) -> QueuePort:
    """
    Build the configured QueuePort implementation.

    Pass ``redis_client`` in tests to inject FakeAsyncRedis without a real server.
    """
    backend = normalize_queue_backend(settings.ai_queue_backend)
    visibility = float(settings.ai_queue_visibility_timeout)
    wid = worker_id or DEFAULT_WORKER_ID

    if backend == "inmemory":
        queue = InMemoryQueue(visibility_timeout=visibility)
        queue.worker_id = wid
        return queue

    client = redis_client if redis_client is not None else create_redis_client(
        settings.redis_url
    )
    return RedisQueue(
        client,
        queue_name=settings.ai_queue_name,
        visibility_timeout=visibility,
        worker_id=wid,
    )

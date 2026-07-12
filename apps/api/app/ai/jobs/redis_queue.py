"""Redis-backed AI job queue (Sprint 27).

Uses Redis sorted sets for the ready queue (priority) plus a processing hash and
per-job locks for visibility / single-worker ownership.
"""

from __future__ import annotations

import json
import time
from typing import Any, Protocol
from uuid import UUID

from app.ai.jobs.queue import QueueDiagnostics


class AsyncRedisClient(Protocol):
    """Minimal async Redis surface used by RedisQueue (mockable in tests)."""

    async def zadd(self, name: str, mapping: dict[str, float]) -> int: ...

    async def zpopmax(self, name: str, count: int = 1) -> list[Any]: ...

    async def zrange(self, name: str, start: int, end: int, **kwargs: Any) -> list[Any]: ...

    async def zcard(self, name: str) -> int: ...

    async def zrem(self, name: str, *values: str) -> int: ...

    async def hset(self, name: str, key: str | None = None, value: str | None = None, mapping: dict[str, str] | None = None) -> int: ...

    async def hget(self, name: str, key: str) -> str | None: ...

    async def hdel(self, name: str, *keys: str) -> int: ...

    async def hgetall(self, name: str) -> dict[str, str]: ...

    async def set(
        self,
        name: str,
        value: str,
        *,
        nx: bool = False,
        ex: int | None = None,
    ) -> bool | None: ...

    async def delete(self, *names: str) -> int: ...

    async def get(self, name: str) -> str | None: ...


class RedisQueue:
    """
    Distributed QueuePort backed by Redis.

    Ready jobs live in a ZSET (score = priority). Dequeue moves a job into the
    processing hash under a per-job NX lock. If the worker crashes, visibility
    timeout reclaim returns the job to the ready set.
    """

    backend_name = "redis"

    def __init__(
        self,
        client: AsyncRedisClient,
        *,
        queue_name: str,
        visibility_timeout: float = 60.0,
        worker_id: str | None = None,
    ) -> None:
        self._redis = client
        self._queue_name = queue_name.rstrip(":")
        self._ready = f"{self._queue_name}:ready"
        self._processing = f"{self._queue_name}:processing"
        self._lock_prefix = f"{self._queue_name}:lock:"
        self._visibility_timeout = float(visibility_timeout)
        self.worker_id = worker_id or "redis-worker"

    async def enqueue(self, job_id: UUID, *, priority: int = 0) -> None:
        member = str(job_id)
        await self._redis.zrem(self._ready, member)
        await self._redis.hdel(self._processing, member)
        await self._redis.delete(self._lock_key(member))
        # Higher priority first via zpopmax.
        await self._redis.zadd(self._ready, {member: float(priority)})

    async def dequeue(self) -> UUID | None:
        await self.reclaim_expired()
        popped = await self._redis.zpopmax(self._ready, count=1)
        if not popped:
            return None
        # redis-py returns [(member, score), ...]
        member, score = self._parse_zpop(popped[0])
        lock_ok = await self._redis.set(
            self._lock_key(member),
            self.worker_id,
            nx=True,
            ex=max(1, int(self._visibility_timeout)),
        )
        if not lock_ok:
            # Another worker won the race — requeue and try nothing this round.
            await self._redis.zadd(self._ready, {member: float(score)})
            return None

        payload = json.dumps(
            {
                "job_id": member,
                "priority": float(score),
                "worker_id": self.worker_id,
                "claimed_at": time.time(),
            }
        )
        await self._redis.hset(self._processing, mapping={member: payload})
        return UUID(member)

    async def ack(self, job_id: UUID) -> None:
        member = str(job_id)
        await self._redis.hdel(self._processing, member)
        await self._redis.delete(self._lock_key(member))

    async def cancel(self, job_id: UUID) -> bool:
        member = str(job_id)
        removed_ready = await self._redis.zrem(self._ready, member)
        removed_proc = await self._redis.hdel(self._processing, member)
        await self._redis.delete(self._lock_key(member))
        return bool(removed_ready or removed_proc)

    async def size(self) -> int:
        await self.reclaim_expired()
        return int(await self._redis.zcard(self._ready))

    async def peek(self) -> UUID | None:
        await self.reclaim_expired()
        rows = await self._redis.zrange(self._ready, -1, -1)
        if not rows:
            return None
        return UUID(str(rows[0]))

    async def reclaim_expired(self) -> int:
        """Return processing jobs whose visibility window elapsed to the ready set."""
        now = time.time()
        processing = await self._redis.hgetall(self._processing)
        reclaimed = 0
        for member, raw in processing.items():
            try:
                data = json.loads(raw)
                claimed_at = float(data.get("claimed_at", 0))
                priority = float(data.get("priority", 0))
            except (TypeError, ValueError, json.JSONDecodeError):
                claimed_at = 0.0
                priority = 0.0
            if now - claimed_at < self._visibility_timeout:
                continue
            await self._redis.hdel(self._processing, member)
            await self._redis.delete(self._lock_key(member))
            await self._redis.zadd(self._ready, {member: priority})
            reclaimed += 1
        return reclaimed

    def diagnostics(self) -> QueueDiagnostics:
        # Length is best-effort sync snapshot; callers preferring live size use await size().
        return QueueDiagnostics(
            backend=self.backend_name,
            queue_length=-1,
            worker_id=self.worker_id,
            visibility_timeout=self._visibility_timeout,
        )

    async def diagnostics_async(self) -> QueueDiagnostics:
        return QueueDiagnostics(
            backend=self.backend_name,
            queue_length=await self.size(),
            worker_id=self.worker_id,
            visibility_timeout=self._visibility_timeout,
        )

    def _lock_key(self, member: str) -> str:
        return f"{self._lock_prefix}{member}"

    @staticmethod
    def _parse_zpop(item: Any) -> tuple[str, float]:
        if isinstance(item, (list, tuple)) and len(item) >= 2:
            return str(item[0]), float(item[1])
        raise TypeError(f"Unexpected zpopmax item: {item!r}")

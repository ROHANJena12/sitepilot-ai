"""Queue port and in-memory queue for AI generation jobs."""

from __future__ import annotations

import asyncio
import time
from collections import deque
from dataclasses import dataclass, field
from typing import Protocol
from uuid import UUID


@dataclass(frozen=True, slots=True)
class QueueDiagnostics:
    """Lightweight queue observability (not part of job API DTOs)."""

    backend: str
    queue_length: int
    worker_id: str | None = None
    visibility_timeout: float | None = None


class QueuePort(Protocol):
    """
    Abstraction over a job queue.

    Sprint 26: InMemoryQueue. Sprint 27: RedisQueue also implements this port.
    ``ack`` confirms a dequeued job finished (no-op for simple in-memory use).
    """

    async def enqueue(self, job_id: UUID, *, priority: int = 0) -> None: ...

    async def dequeue(self) -> UUID | None: ...

    async def ack(self, job_id: UUID) -> None: ...

    async def cancel(self, job_id: UUID) -> bool: ...

    async def size(self) -> int: ...

    async def peek(self) -> UUID | None: ...


@dataclass(order=True)
class _QueuedItem:
    # Lower sort key = higher priority (negate priority for max-heap via min order).
    sort_key: tuple[int, int]
    job_id: UUID = field(compare=False)


@dataclass
class _InFlight:
    job_id: UUID
    claimed_at: float
    priority: int = 0


class InMemoryQueue:
    """
    Process-local FIFO priority queue with optional visibility semantics.

    Higher ``priority`` values dequeue first. Same priority → insertion order.
    Not durable across process restarts.
    """

    backend_name = "inmemory"

    def __init__(self, *, visibility_timeout: float = 60.0) -> None:
        self._items: deque[_QueuedItem] = deque()
        self._inflight: dict[UUID, _InFlight] = {}
        self._priorities: dict[UUID, int] = {}
        self._seq = 0
        self._lock = asyncio.Lock()
        self._visibility_timeout = float(visibility_timeout)
        self.worker_id: str | None = None

    async def enqueue(self, job_id: UUID, *, priority: int = 0) -> None:
        async with self._lock:
            self._items = deque(i for i in self._items if i.job_id != job_id)
            self._inflight.pop(job_id, None)
            self._seq += 1
            self._priorities[job_id] = int(priority)
            self._items.append(
                _QueuedItem(sort_key=(-int(priority), self._seq), job_id=job_id)
            )
            self._resort()

    async def dequeue(self) -> UUID | None:
        async with self._lock:
            self._reclaim_expired_unlocked()
            if not self._items:
                return None
            item = self._items.popleft()
            self._inflight[item.job_id] = _InFlight(
                job_id=item.job_id,
                claimed_at=time.monotonic(),
                priority=self._priorities.get(item.job_id, 0),
            )
            return item.job_id

    async def ack(self, job_id: UUID) -> None:
        async with self._lock:
            self._inflight.pop(job_id, None)
            self._priorities.pop(job_id, None)

    async def cancel(self, job_id: UUID) -> bool:
        async with self._lock:
            before = len(self._items)
            self._items = deque(i for i in self._items if i.job_id != job_id)
            removed_ready = len(self._items) < before
            removed_inflight = self._inflight.pop(job_id, None) is not None
            if removed_ready or removed_inflight:
                self._priorities.pop(job_id, None)
                return True
            return False

    async def size(self) -> int:
        async with self._lock:
            self._reclaim_expired_unlocked()
            return len(self._items)

    async def peek(self) -> UUID | None:
        async with self._lock:
            self._reclaim_expired_unlocked()
            if not self._items:
                return None
            return self._items[0].job_id

    def diagnostics(self) -> QueueDiagnostics:
        return QueueDiagnostics(
            backend=self.backend_name,
            queue_length=len(self._items),
            worker_id=self.worker_id,
            visibility_timeout=self._visibility_timeout,
        )

    def _reclaim_expired_unlocked(self) -> None:
        now = time.monotonic()
        expired = [
            job_id
            for job_id, meta in self._inflight.items()
            if now - meta.claimed_at >= self._visibility_timeout
        ]
        for job_id in expired:
            meta = self._inflight.pop(job_id)
            self._seq += 1
            priority = meta.priority
            self._priorities[job_id] = priority
            self._items.append(
                _QueuedItem(sort_key=(-int(priority), self._seq), job_id=job_id)
            )
        if expired:
            self._resort()

    def _resort(self) -> None:
        ordered = sorted(self._items)
        self._items = deque(ordered)

    def clear(self) -> None:
        """Test helper — drop all pending / in-flight ids."""
        self._items.clear()
        self._inflight.clear()
        self._priorities.clear()
        self._seq = 0

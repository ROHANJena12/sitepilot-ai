"""Unit tests for InMemoryQueue (Sprint 26)."""

from __future__ import annotations

from uuid import uuid4

import pytest

from app.ai.jobs.queue import InMemoryQueue


@pytest.mark.asyncio
async def test_enqueue_dequeue_fifo_same_priority() -> None:
    q = InMemoryQueue()
    a, b, c = uuid4(), uuid4(), uuid4()
    await q.enqueue(a)
    await q.enqueue(b)
    await q.enqueue(c)
    assert await q.size() == 3
    assert await q.peek() == a
    assert await q.dequeue() == a
    assert await q.dequeue() == b
    assert await q.dequeue() == c
    assert await q.dequeue() is None
    assert await q.size() == 0


@pytest.mark.asyncio
async def test_higher_priority_dequeues_first() -> None:
    q = InMemoryQueue()
    low, high = uuid4(), uuid4()
    await q.enqueue(low, priority=1)
    await q.enqueue(high, priority=10)
    assert await q.dequeue() == high
    assert await q.dequeue() == low


@pytest.mark.asyncio
async def test_cancel_removes_pending() -> None:
    q = InMemoryQueue()
    a, b = uuid4(), uuid4()
    await q.enqueue(a)
    await q.enqueue(b)
    assert await q.cancel(a) is True
    assert await q.cancel(a) is False
    assert await q.dequeue() == b
    assert await q.peek() is None

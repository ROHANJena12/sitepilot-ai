"""Sprint 27 — Redis queue, factory, worker (mocked Redis)."""

from __future__ import annotations

import asyncio
from uuid import uuid4

import pytest
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.ai.features import AIFeature
from app.ai.jobs.factory import create_job_queue, normalize_queue_backend
from app.ai.jobs.fake_redis import FakeAsyncRedis
from app.ai.jobs.queue import InMemoryQueue
from app.ai.jobs.redis_queue import RedisQueue
from app.ai.jobs.redis_worker import RedisWorker
from app.ai.jobs.worker import BackgroundWorker
from app.core.config import Environment, Settings
from app.services.ai_job_runner import AIJobRunner
from tests.api.test_ai import StubAIService, _seed


def _settings(**overrides) -> Settings:
    base = dict(
        app_name="sitepilot-api",
        app_version="0.1.0",
        environment=Environment.TESTING,
        debug=False,
        log_level="WARNING",
        database_url="postgresql+asyncpg://sitepilot:sitepilot@localhost:5434/sitepilot_test",
        redis_url="redis://localhost:6379/15",
        cors_origins=["http://localhost:3000"],
        secret_key="test-secret",
        ai_queue_backend="redis",
        ai_queue_name="test:ai:jobs",
        ai_queue_visibility_timeout=1.0,
        ai_worker_poll_interval=0.01,
        ai_max_concurrent_workers=1,
    )
    base.update(overrides)
    return Settings(**base)


def test_normalize_queue_backend() -> None:
    assert normalize_queue_backend("inmemory") == "inmemory"
    assert normalize_queue_backend("IN-MEMORY") == "inmemory"
    assert normalize_queue_backend("redis") == "redis"
    with pytest.raises(ValueError):
        normalize_queue_backend("celery")


def test_queue_factory_selects_inmemory() -> None:
    q = create_job_queue(_settings(ai_queue_backend="inmemory"))
    assert isinstance(q, InMemoryQueue)
    assert q.diagnostics().backend == "inmemory"


def test_queue_factory_selects_redis_with_client() -> None:
    fake = FakeAsyncRedis()
    q = create_job_queue(
        _settings(ai_queue_backend="redis"),
        redis_client=fake,
        worker_id="worker-a",
    )
    assert isinstance(q, RedisQueue)
    assert q.worker_id == "worker-a"


@pytest.mark.asyncio
async def test_redis_enqueue_dequeue_ack() -> None:
    fake = FakeAsyncRedis()
    q = RedisQueue(fake, queue_name="t:jobs", visibility_timeout=30, worker_id="w1")
    a, b = uuid4(), uuid4()
    await q.enqueue(a, priority=1)
    await q.enqueue(b, priority=10)
    assert await q.size() == 2
    assert await q.peek() == b
    first = await q.dequeue()
    assert first == b
    assert await q.size() == 1
    await q.ack(b)
    second = await q.dequeue()
    assert second == a
    await q.ack(a)
    assert await q.dequeue() is None


@pytest.mark.asyncio
async def test_redis_cancel() -> None:
    fake = FakeAsyncRedis()
    q = RedisQueue(fake, queue_name="t:jobs", visibility_timeout=30)
    a, b = uuid4(), uuid4()
    await q.enqueue(a)
    await q.enqueue(b)
    assert await q.cancel(a) is True
    assert await q.dequeue() == b
    await q.ack(b)


@pytest.mark.asyncio
async def test_visibility_timeout_reclaims() -> None:
    fake = FakeAsyncRedis()
    q = RedisQueue(fake, queue_name="t:vis", visibility_timeout=0.05, worker_id="w1")
    job = uuid4()
    await q.enqueue(job)
    claimed = await q.dequeue()
    assert claimed == job
    # Still in processing — not ready
    assert await q.size() == 0
    # Expire visibility
    await asyncio.sleep(0.06)
    assert await q.reclaim_expired() == 1
    again = await q.dequeue()
    assert again == job
    await q.ack(job)


@pytest.mark.asyncio
async def test_distributed_lock_prevents_double_claim() -> None:
    fake = FakeAsyncRedis()
    q1 = RedisQueue(fake, queue_name="t:lock", visibility_timeout=30, worker_id="w1")
    q2 = RedisQueue(fake, queue_name="t:lock", visibility_timeout=30, worker_id="w2")
    job = uuid4()
    await q1.enqueue(job)
    first = await q1.dequeue()
    assert first == job
    # Manually put same id back without releasing lock (simulate race)
    await fake.zadd("t:lock:ready", {str(job): 0.0})
    second = await q2.dequeue()
    # Lock held by w1 → q2 requeues and returns None
    assert second is None
    await q1.ack(job)


@pytest.mark.asyncio
async def test_multiple_workers_consume_distinct_jobs() -> None:
    fake = FakeAsyncRedis()
    q1 = RedisQueue(fake, queue_name="t:multi", visibility_timeout=30, worker_id="w1")
    q2 = RedisQueue(fake, queue_name="t:multi", visibility_timeout=30, worker_id="w2")
    jobs = [uuid4() for _ in range(4)]
    for j in jobs:
        await q1.enqueue(j)

    claimed: list = []
    for _ in range(4):
        a = await q1.dequeue()
        b = await q2.dequeue()
        if a:
            claimed.append(a)
            await q1.ack(a)
        if b:
            claimed.append(b)
            await q2.ack(b)
    assert set(claimed) == set(jobs)


@pytest.mark.asyncio
async def test_inmemory_ack_and_visibility() -> None:
    q = InMemoryQueue(visibility_timeout=0.05)
    job = uuid4()
    await q.enqueue(job)
    assert await q.dequeue() == job
    assert await q.size() == 0
    await asyncio.sleep(0.06)
    assert await q.size() == 1  # reclaimed
    assert await q.dequeue() == job
    await q.ack(job)
    assert await q.dequeue() is None


@pytest.mark.asyncio
async def test_background_worker_acks(
    db_session: AsyncSession, db_engine
) -> None:
    _audit, finding, _rec = await _seed(db_session)
    await db_session.commit()
    queue = InMemoryQueue(visibility_timeout=60)
    from app.application.ai.jobs.queue_generation import QueueGenerationUseCase

    accepted = await QueueGenerationUseCase(db_session, queue).execute(
        feature=AIFeature.FINDING,
        resource_id=finding.id,
    )
    await db_session.commit()
    factory = async_sessionmaker(db_engine, expire_on_commit=False, class_=AsyncSession)
    worker = BackgroundWorker(queue, AIJobRunner(StubAIService()), factory)
    processed = await worker.process_next()
    assert processed == accepted.accepted.job_id
    assert await queue.dequeue() is None


@pytest.mark.asyncio
async def test_redis_worker_run_once_and_restart(
    db_session: AsyncSession, db_engine
) -> None:
    _audit, finding, _rec = await _seed(db_session)
    await db_session.commit()
    fake = FakeAsyncRedis()
    queue = RedisQueue(fake, queue_name="t:rw", visibility_timeout=30, worker_id="w1")
    from app.application.ai.jobs.queue_generation import QueueGenerationUseCase

    accepted = await QueueGenerationUseCase(db_session, queue).execute(
        feature=AIFeature.FINDING,
        resource_id=finding.id,
    )
    await db_session.commit()

    factory = async_sessionmaker(db_engine, expire_on_commit=False, class_=AsyncSession)
    worker = RedisWorker(
        queue,
        AIJobRunner(StubAIService()),
        factory,
        worker_id="w1",
        poll_interval=0.01,
    )
    assert await worker.run_once() == accepted.accepted.job_id
    # Restart worker on empty queue
    worker2 = RedisWorker(
        queue,
        AIJobRunner(StubAIService()),
        factory,
        worker_id="w2",
        poll_interval=0.01,
    )
    assert await worker2.run_once() is None


@pytest.mark.asyncio
async def test_graceful_shutdown() -> None:
    fake = FakeAsyncRedis()
    queue = RedisQueue(fake, queue_name="t:shut", visibility_timeout=30)
    from unittest.mock import MagicMock

    session_factory = MagicMock()
    worker = RedisWorker(
        queue,
        AIJobRunner(StubAIService()),
        session_factory,
        worker_id="w1",
        poll_interval=0.01,
    )

    async def _stop_soon() -> None:
        await asyncio.sleep(0.05)
        worker.request_shutdown()

    await asyncio.gather(worker.run_forever(), _stop_soon())
    assert worker.stopping is True


@pytest.mark.asyncio
async def test_diagnostics_async() -> None:
    fake = FakeAsyncRedis()
    q = RedisQueue(fake, queue_name="t:diag", visibility_timeout=12.5, worker_id="diag-1")
    await q.enqueue(uuid4())
    diag = await q.diagnostics_async()
    assert diag.backend == "redis"
    assert diag.queue_length == 1
    assert diag.worker_id == "diag-1"
    assert diag.visibility_timeout == 12.5


@pytest.mark.asyncio
async def test_queue_generation_can_defer_enqueue(
    db_session: AsyncSession,
) -> None:
    """HTTP path uses enqueue=False → commit → enqueue (Sprint 27.5)."""
    _audit, finding, _rec = await _seed(db_session)
    await db_session.commit()
    queue = InMemoryQueue()
    from app.application.ai.jobs.queue_generation import QueueGenerationUseCase

    result = await QueueGenerationUseCase(db_session, queue).execute(
        feature=AIFeature.FINDING,
        resource_id=finding.id,
        enqueue=False,
    )
    assert await queue.size() == 0
    await db_session.commit()
    await queue.enqueue(result.accepted.job_id, priority=result.priority)
    assert await queue.peek() == result.accepted.job_id


@pytest.mark.asyncio
async def test_job_not_found_skips_ack_for_visibility_reclaim(
    db_engine,
) -> None:
    """Premature dequeue must not ack — visibility reclaim can retry."""
    fake = FakeAsyncRedis()
    queue = RedisQueue(
        fake, queue_name="t:nofound", visibility_timeout=0.05, worker_id="w1"
    )
    missing = uuid4()
    await queue.enqueue(missing)
    factory = async_sessionmaker(db_engine, expire_on_commit=False, class_=AsyncSession)
    worker = RedisWorker(
        queue,
        AIJobRunner(StubAIService()),
        factory,
        worker_id="w1",
        poll_interval=0.01,
    )
    assert await worker.run_once() == missing
    await asyncio.sleep(0.08)
    await queue.reclaim_expired()
    assert await queue.dequeue() == missing

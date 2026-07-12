"""Repository + runner + worker tests for AI generation jobs."""

from __future__ import annotations

from uuid import uuid4

import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.ai.features import AIFeature
from app.ai.jobs.queue import InMemoryQueue
from app.ai.jobs.worker import BackgroundWorker
from app.application.ai.exceptions import (
    JobAlreadyCompletedError,
    JobAlreadyRunningError,
    JobNotCompleteError,
    JobNotFoundError,
)
from app.application.ai.jobs.cancel_generation_job import CancelGenerationJobUseCase
from app.application.ai.jobs.get_job_result import GetGenerationJobResultUseCase
from app.application.ai.jobs.queue_generation import QueueGenerationUseCase
from app.repositories.ai_generation_job import AIGenerationJobRepository
from app.services.ai_job_runner import AIJobRunner
from tests.api.test_ai import StubAIService, _seed


@pytest_asyncio.fixture
async def seeded(db_session: AsyncSession):
    audit, finding, rec = await _seed(db_session)
    await db_session.commit()
    return audit, finding, rec


@pytest.mark.asyncio
async def test_job_repository_lifecycle(db_session: AsyncSession, seeded) -> None:
    _audit, finding, _rec = seeded
    repo = AIGenerationJobRepository(db_session)
    job = await repo.create(
        feature="finding",
        entity_type="finding",
        entity_id="seo.viewport.missing",
        resource_id=finding.id,
        report_hash="hash",
        audit_id=_audit.id,
    )
    assert job.status == "queued"
    job = await repo.mark_running(job, worker="test")
    assert job.status == "running"
    assert job.attempt == 1
    assert job.worker == "test"
    gid = uuid4()
    job = await repo.mark_completed(job, generation_id=gid)
    assert job.status == "completed"
    assert job.generation_id == gid


@pytest.mark.asyncio
async def test_runner_completes_and_persists(
    db_session: AsyncSession, seeded
) -> None:
    _audit, finding, _rec = seeded
    stub = StubAIService()
    queue = InMemoryQueue()
    accepted = await QueueGenerationUseCase(db_session, queue).execute(
        feature=AIFeature.FINDING,
        resource_id=finding.id,
    )
    await db_session.commit()

    runner = AIJobRunner(stub, worker_name="test-runner")
    job = await runner.run(db_session, accepted.accepted.job_id)
    await db_session.commit()

    assert job.status == "completed"
    assert job.generation_id is not None
    assert len(stub.calls) == 1


@pytest.mark.asyncio
async def test_runner_marks_failed_on_error(
    db_session: AsyncSession, seeded
) -> None:
    _audit, finding, _rec = seeded
    stub = StubAIService()
    stub.fail_with = RuntimeError("provider down")
    queue = InMemoryQueue()
    accepted = await QueueGenerationUseCase(db_session, queue).execute(
        feature=AIFeature.FINDING,
        resource_id=finding.id,
    )
    await db_session.commit()

    job = await AIJobRunner(stub).run(db_session, accepted.accepted.job_id)
    await db_session.commit()
    assert job.status == "failed"
    assert "provider down" in (job.error or "")


@pytest.mark.asyncio
async def test_worker_process_next(
    db_session: AsyncSession,
    db_engine,
    seeded,
) -> None:
    _audit, finding, _rec = seeded
    stub = StubAIService()
    queue = InMemoryQueue()
    factory = async_sessionmaker(db_engine, expire_on_commit=False, class_=AsyncSession)

    async with factory() as session:
        accepted = await QueueGenerationUseCase(session, queue).execute(
            feature=AIFeature.FINDING,
            resource_id=finding.id,
        )
        await session.commit()
        job_id = accepted.accepted.job_id

    worker = BackgroundWorker(queue, AIJobRunner(stub), factory)
    processed = await worker.process_next()
    assert processed == job_id
    assert await queue.size() == 0

    async with factory() as session:
        row = await AIGenerationJobRepository(session).get(job_id)
        assert row is not None
        assert row.status == "completed"


@pytest.mark.asyncio
async def test_cancel_queued_job(db_session: AsyncSession, seeded) -> None:
    _audit, finding, _rec = seeded
    queue = InMemoryQueue()
    accepted = await QueueGenerationUseCase(db_session, queue).execute(
        feature=AIFeature.FINDING,
        resource_id=finding.id,
    )
    await db_session.commit()
    assert await queue.size() == 1

    result = await CancelGenerationJobUseCase(db_session, queue).execute(
        accepted.accepted.job_id
    )
    await db_session.commit()
    assert result.job.status == "cancelled"
    assert await queue.size() == 0


@pytest.mark.asyncio
async def test_cancel_running_rejected(db_session: AsyncSession, seeded) -> None:
    _audit, finding, _rec = seeded
    repo = AIGenerationJobRepository(db_session)
    job = await repo.create(
        feature="finding",
        entity_type="finding",
        entity_id="seo.viewport.missing",
        resource_id=finding.id,
        report_hash="h",
        audit_id=_audit.id,
    )
    await repo.mark_running(job, worker="w")
    await db_session.commit()

    with pytest.raises(JobAlreadyRunningError):
        await CancelGenerationJobUseCase(db_session, InMemoryQueue()).execute(job.id)


@pytest.mark.asyncio
async def test_cancel_completed_rejected(db_session: AsyncSession, seeded) -> None:
    _audit, finding, _rec = seeded
    repo = AIGenerationJobRepository(db_session)
    job = await repo.create(
        feature="finding",
        entity_type="finding",
        entity_id="seo.viewport.missing",
        resource_id=finding.id,
        report_hash="h",
        audit_id=_audit.id,
    )
    await repo.mark_running(job, worker="w")
    await repo.mark_completed(job, generation_id=uuid4())
    await db_session.commit()

    with pytest.raises(JobAlreadyCompletedError):
        await CancelGenerationJobUseCase(db_session, InMemoryQueue()).execute(job.id)


@pytest.mark.asyncio
async def test_result_before_complete_raises(db_session: AsyncSession, seeded) -> None:
    _audit, finding, _rec = seeded
    repo = AIGenerationJobRepository(db_session)
    job = await repo.create(
        feature="finding",
        entity_type="finding",
        entity_id="seo.viewport.missing",
        resource_id=finding.id,
        report_hash="h",
        audit_id=_audit.id,
    )
    await db_session.commit()
    with pytest.raises(JobNotCompleteError):
        await GetGenerationJobResultUseCase(db_session).execute(job.id)


@pytest.mark.asyncio
async def test_job_not_found(db_session: AsyncSession) -> None:
    with pytest.raises(JobNotFoundError):
        await GetGenerationJobResultUseCase(db_session).execute(uuid4())

"""Sprint 26.1 — AI job progress, timing, worker identity, cancel reasons."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from uuid import uuid4

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.ai.features import AIFeature
from app.ai.jobs.cancel_reason import CancelReason
from app.ai.jobs.identity import DEFAULT_WORKER_ID, LOCAL_WORKER_ID
from app.ai.jobs.progress import JobProgress
from app.ai.jobs.queue import InMemoryQueue
from app.application.ai.jobs.cancel_generation_job import CancelGenerationJobUseCase
from app.application.ai.jobs.get_generation_job import GetGenerationJobUseCase, job_to_dto
from app.application.ai.jobs.queue_generation import QueueGenerationUseCase
from app.repositories.ai_generation_job import AIGenerationJobRepository
from app.schemas.ai_job import GenerationJobDTO
from app.services.ai_job_runner import AIJobRunner
from tests.api.test_ai import StubAIService, _seed


@pytest.mark.asyncio
async def test_progress_lifecycle(db_session: AsyncSession) -> None:
    audit, finding, _rec = await _seed(db_session)
    await db_session.commit()
    stub = StubAIService()
    queue = InMemoryQueue()

    accepted = await QueueGenerationUseCase(db_session, queue).execute(
        feature=AIFeature.FINDING,
        resource_id=finding.id,
    )
    await db_session.commit()
    repo = AIGenerationJobRepository(db_session)
    job = await repo.get(accepted.accepted.job_id)
    assert job is not None
    assert job.progress == JobProgress.QUEUED

    job = await AIJobRunner(stub).run(db_session, job.id)
    await db_session.commit()
    assert job.status == "completed"
    assert job.progress == JobProgress.COMPLETED
    assert job.worker == DEFAULT_WORKER_ID


@pytest.mark.asyncio
async def test_failed_keeps_progress(db_session: AsyncSession) -> None:
    _audit, finding, _rec = await _seed(db_session)
    await db_session.commit()
    stub = StubAIService()
    stub.fail_with = RuntimeError("boom")
    queue = InMemoryQueue()
    accepted = await QueueGenerationUseCase(db_session, queue).execute(
        feature=AIFeature.FINDING,
        resource_id=finding.id,
    )
    await db_session.commit()

    job = await AIJobRunner(stub).run(db_session, accepted.accepted.job_id)
    await db_session.commit()
    assert job.status == "failed"
    assert job.progress == JobProgress.PROVIDER_REQUEST
    assert job.last_error is not None
    assert "boom" in job.last_error


@pytest.mark.asyncio
async def test_timing_calculations(db_session: AsyncSession) -> None:
    audit, finding, _rec = await _seed(db_session)
    repo = AIGenerationJobRepository(db_session)
    job = await repo.create(
        feature="finding",
        entity_type="finding",
        entity_id="seo.viewport.missing",
        resource_id=finding.id,
        report_hash="h",
        audit_id=audit.id,
    )
    base = datetime.now(UTC)
    job.queued_at = base
    job.started_at = base + timedelta(milliseconds=150)
    job.completed_at = base + timedelta(milliseconds=400)
    await db_session.flush()

    timing = AIGenerationJobRepository.compute_timing(job)
    assert timing.queue_wait_ms == 150
    assert timing.execution_ms == 250
    assert timing.total_duration_ms == 400


@pytest.mark.asyncio
async def test_worker_identity_centralized(db_session: AsyncSession) -> None:
    assert LOCAL_WORKER_ID == "local-worker-1"
    assert DEFAULT_WORKER_ID == LOCAL_WORKER_ID
    _audit, finding, _rec = await _seed(db_session)
    await db_session.commit()
    queue = InMemoryQueue()
    accepted = await QueueGenerationUseCase(db_session, queue).execute(
        feature=AIFeature.FINDING,
        resource_id=finding.id,
    )
    await db_session.commit()
    job = await AIJobRunner(StubAIService()).run(db_session, accepted.accepted.job_id)
    await db_session.commit()
    assert job.worker == "local-worker-1"


@pytest.mark.asyncio
async def test_cancellation_reason(db_session: AsyncSession) -> None:
    _audit, finding, _rec = await _seed(db_session)
    await db_session.commit()
    queue = InMemoryQueue()
    accepted = await QueueGenerationUseCase(db_session, queue).execute(
        feature=AIFeature.FINDING,
        resource_id=finding.id,
    )
    await db_session.commit()

    result = await CancelGenerationJobUseCase(db_session, queue).execute(
        accepted.accepted.job_id,
        cancel_reason=CancelReason.SUPERSEDED,
    )
    await db_session.commit()
    assert result.job.status == "cancelled"
    assert result.job.cancel_reason == "SUPERSEDED"
    assert result.job.progress == JobProgress.QUEUED


@pytest.mark.asyncio
async def test_retry_metadata_defaults(db_session: AsyncSession) -> None:
    audit, finding, _rec = await _seed(db_session)
    repo = AIGenerationJobRepository(db_session)
    job = await repo.create(
        feature="finding",
        entity_type="finding",
        entity_id="seo.viewport.missing",
        resource_id=finding.id,
        report_hash="h",
        audit_id=audit.id,
        max_attempts=3,
    )
    await db_session.commit()
    assert job.attempt == 0
    assert job.max_attempts == 3
    assert job.next_retry_at is None
    assert job.last_error is None

    job = await repo.mark_running(job, worker=DEFAULT_WORKER_ID)
    assert job.attempt == 1
    job = await repo.mark_failed(job, error="temporary")
    assert job.last_error == "temporary"
    assert job.error == "temporary"


@pytest.mark.asyncio
async def test_dto_serialization_completed(db_session: AsyncSession) -> None:
    _audit, finding, _rec = await _seed(db_session)
    await db_session.commit()
    queue = InMemoryQueue()
    accepted = await QueueGenerationUseCase(db_session, queue).execute(
        feature=AIFeature.FINDING,
        resource_id=finding.id,
    )
    await db_session.commit()
    job = await AIJobRunner(StubAIService()).run(db_session, accepted.accepted.job_id)
    await db_session.commit()

    dto = await job_to_dto(db_session, job)
    assert isinstance(dto, GenerationJobDTO)
    payload = dto.model_dump(mode="json")
    assert payload["status"] == "completed"
    assert payload["progress"] == 100
    assert payload["generation_id"] is not None
    assert payload["latest_version"] == 1
    assert payload["result_url"] == f"/api/v1/jobs/{job.id}/result"
    assert payload["worker"] == DEFAULT_WORKER_ID
    assert payload["queue_wait_ms"] is not None
    assert payload["execution_ms"] is not None
    assert payload["total_duration_ms"] is not None
    assert "max_attempts" in payload


@pytest.mark.asyncio
async def test_get_use_case_completed_metadata(db_session: AsyncSession) -> None:
    _audit, finding, _rec = await _seed(db_session)
    await db_session.commit()
    queue = InMemoryQueue()
    accepted = await QueueGenerationUseCase(db_session, queue).execute(
        feature=AIFeature.FINDING,
        resource_id=finding.id,
    )
    await db_session.commit()
    await AIJobRunner(StubAIService()).run(db_session, accepted.accepted.job_id)
    await db_session.commit()

    result = await GetGenerationJobUseCase(db_session).execute(accepted.accepted.job_id)
    assert result.job.result_url is not None
    assert result.job.latest_version == 1
    assert result.job.generation_id is not None

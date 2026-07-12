"""Sprint 26.3 — AI job lifecycle management."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from uuid import uuid4

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.ai.features import AIFeature
from app.ai.jobs.lifecycle import (
    age_ms,
    classify_duration,
    classify_queue_wait,
    default_expires_at,
    is_cleanup_candidate,
    is_expired,
    is_stale,
)
from app.ai.jobs.queue import InMemoryQueue
from app.ai.jobs.retention import (
    JOB_RETENTION_CANCELLED_DAYS,
    JOB_RETENTION_COMPLETED_DAYS,
    JOB_RETENTION_FAILED_DAYS,
    JOB_STALE_RUNNING_AFTER,
    DurationClass,
    QueueClass,
)
from app.application.ai.jobs.get_generation_job import job_to_dto
from app.application.ai.jobs.queue_generation import QueueGenerationUseCase
from app.models.ai_generation_job import AIGenerationJob
from app.repositories.ai_generation_job import AIGenerationJobRepository
from app.services.ai_job_runner import AIJobRunner
from tests.api.test_ai import StubAIService, _seed


def _job(**kwargs) -> AIGenerationJob:
    now = datetime.now(UTC)
    defaults = dict(
        id=uuid4(),
        feature="finding",
        entity_type="finding",
        entity_id="x",
        resource_id=uuid4(),
        report_hash="",
        status="queued",
        progress=0,
        created_at=now,
        queued_at=now,
        phase_history=[],
    )
    defaults.update(kwargs)
    return AIGenerationJob(**defaults)


def test_retention_constants() -> None:
    assert JOB_RETENTION_COMPLETED_DAYS == 1
    assert JOB_RETENTION_FAILED_DAYS == 7
    assert JOB_RETENTION_CANCELLED_DAYS == 7


def test_expiration_only_for_completed() -> None:
    now = datetime.now(UTC)
    queued = _job(status="queued")
    assert is_expired(queued, now=now) is False

    running = _job(status="running", started_at=now)
    assert is_expired(running, now=now) is False

    completed = _job(
        status="completed",
        completed_at=now - timedelta(hours=25),
        expires_at=now - timedelta(hours=1),
    )
    assert is_expired(completed, now=now) is True

    fresh = _job(
        status="completed",
        completed_at=now,
        expires_at=default_expires_at(now),
    )
    assert is_expired(fresh, now=now) is False


def test_cleanup_eligibility() -> None:
    now = datetime.now(UTC)
    expired_completed = _job(
        status="completed",
        completed_at=now - timedelta(days=2),
        expires_at=now - timedelta(hours=1),
    )
    assert is_cleanup_candidate(expired_completed, now=now) is True

    old_failed = _job(
        status="failed",
        completed_at=now - timedelta(days=JOB_RETENTION_FAILED_DAYS + 1),
    )
    assert is_cleanup_candidate(old_failed, now=now) is True

    recent_failed = _job(
        status="failed",
        completed_at=now - timedelta(days=1),
    )
    assert is_cleanup_candidate(recent_failed, now=now) is False

    old_cancelled = _job(
        status="cancelled",
        completed_at=now - timedelta(days=JOB_RETENTION_CANCELLED_DAYS + 1),
    )
    assert is_cleanup_candidate(old_cancelled, now=now) is True

    running = _job(status="running", started_at=now)
    assert is_cleanup_candidate(running, now=now) is False


def test_stale_jobs() -> None:
    now = datetime.now(UTC)
    stale = _job(
        status="running",
        started_at=now - JOB_STALE_RUNNING_AFTER - timedelta(seconds=1),
    )
    assert is_stale(stale, now=now) is True

    fresh = _job(status="running", started_at=now)
    assert is_stale(fresh, now=now) is False

    completed = _job(status="completed", completed_at=now, started_at=now)
    assert is_stale(completed, now=now) is False


def test_age_and_classifications() -> None:
    now = datetime.now(UTC)
    job = _job(created_at=now - timedelta(seconds=2))
    assert age_ms(job, now=now) >= 2000

    assert classify_duration(100) == DurationClass.FAST.value
    assert classify_duration(2_000) == DurationClass.NORMAL.value
    assert classify_duration(10_000) == DurationClass.SLOW.value
    assert classify_duration(60_000) == DurationClass.VERY_SLOW.value
    assert classify_duration(None) is None

    assert classify_queue_wait(50) == QueueClass.IMMEDIATE.value
    assert classify_queue_wait(500) == QueueClass.SHORT.value
    assert classify_queue_wait(2_000) == QueueClass.NORMAL.value
    assert classify_queue_wait(10_000) == QueueClass.LONG.value
    assert classify_queue_wait(None) is None


@pytest.mark.asyncio
async def test_mark_completed_sets_expires_at(db_session: AsyncSession) -> None:
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
    job = await repo.mark_running(job, worker="local-worker-1")
    job = await repo.mark_completed(job, generation_id=uuid4())
    await db_session.commit()

    assert job.expires_at is not None
    assert job.completed_at is not None
    assert job.expires_at == default_expires_at(job.completed_at)
    assert AIGenerationJobRepository.is_expired(job) is False
    lifecycle = AIGenerationJobRepository.compute_lifecycle(job)
    assert lifecycle.expired is False
    assert lifecycle.stale is False
    assert lifecycle.age_ms >= 0


@pytest.mark.asyncio
async def test_dto_lifecycle_fields(db_session: AsyncSession) -> None:
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
    payload = dto.model_dump(mode="json")
    assert payload["expires_at"] is not None
    assert payload["expired"] is False
    assert payload["cleanup_candidate"] is False
    assert payload["stale"] is False
    assert payload["age_ms"] is not None
    assert payload["duration_class"] in {
        "FAST",
        "NORMAL",
        "SLOW",
        "VERY_SLOW",
        None,
    }
    assert payload["queue_class"] in {
        "IMMEDIATE",
        "SHORT",
        "NORMAL",
        "LONG",
        None,
    }


@pytest.mark.asyncio
async def test_repo_stale_and_cleanup_helpers(db_session: AsyncSession) -> None:
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
    job = await repo.mark_running(job, worker="local-worker-1")
    job.started_at = datetime.now(UTC) - JOB_STALE_RUNNING_AFTER - timedelta(minutes=1)
    await db_session.flush()

    assert repo.is_stale(job) is True
    assert repo.is_cleanup_candidate(job) is False

    job = await repo.mark_failed(job, error="x", failure_category="INTERNAL")
    job.completed_at = datetime.now(UTC) - timedelta(days=JOB_RETENTION_FAILED_DAYS + 1)
    await db_session.flush()
    assert repo.is_cleanup_candidate(job) is True

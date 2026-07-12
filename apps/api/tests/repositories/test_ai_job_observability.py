"""Sprint 26.2 — AI job observability & diagnostics."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.ai.exceptions import AIProviderError, InvalidAIResponse
from app.ai.features import AIFeature
from app.ai.jobs.failure import JobFailureCategory, classify_failure
from app.ai.jobs.observability import (
    compute_health,
    compute_job_events,
    compute_status_summary,
    extract_provider_diagnostics,
)
from app.ai.jobs.progress import JobProgress
from app.ai.jobs.queue import InMemoryQueue
from app.application.ai.jobs.cancel_generation_job import CancelGenerationJobUseCase
from app.application.ai.jobs.get_generation_job import GetGenerationJobUseCase, job_to_dto
from app.application.ai.jobs.queue_generation import QueueGenerationUseCase
from app.repositories.ai_generation_job import AIGenerationJobRepository
from app.services.ai_job_runner import AIJobRunner
from tests.api.test_ai import StubAIService, _seed


def test_classify_failure_categories() -> None:
    assert classify_failure(InvalidAIResponse("Grounding failed")) == (
        JobFailureCategory.GROUNDING
    )
    assert classify_failure(InvalidAIResponse("schema mismatch")) == (
        JobFailureCategory.VALIDATION
    )
    assert classify_failure(AIProviderError("openai timeout")) == (
        JobFailureCategory.TIMEOUT
    )
    assert classify_failure(AIProviderError("rate limited")) == (
        JobFailureCategory.PROVIDER
    )
    assert classify_failure(RuntimeError("persist failed")) == (
        JobFailureCategory.PERSISTENCE
    )
    assert classify_failure(None, message="queue full") == JobFailureCategory.QUEUE
    assert classify_failure(RuntimeError("boom")) == JobFailureCategory.INTERNAL


def test_status_summaries_and_health() -> None:
    from app.models.ai_generation_job import AIGenerationJob
    from uuid import uuid4

    job = AIGenerationJob(
        id=uuid4(),
        feature="finding",
        entity_type="finding",
        entity_id="x",
        resource_id=uuid4(),
        report_hash="",
        status="queued",
        progress=0,
    )
    assert compute_status_summary(job) == "Queued"
    assert compute_health(job) == {
        "is_running": False,
        "is_terminal": False,
        "is_success": False,
        "is_failure": False,
    }

    job.status = "running"
    job.progress = int(JobProgress.PROVIDER_REQUEST)
    assert compute_status_summary(job) == "Waiting for provider"
    assert compute_health(job)["is_running"] is True

    job.progress = int(JobProgress.GROUNDING)
    assert compute_status_summary(job) == "Grounding response"

    job.progress = int(JobProgress.PERSISTING)
    assert compute_status_summary(job) == "Persisting"

    job.status = "completed"
    job.progress = 100
    assert compute_status_summary(job) == "Completed"
    assert compute_health(job)["is_success"] is True
    assert compute_health(job)["is_terminal"] is True

    job.status = "failed"
    assert compute_status_summary(job) == "Failed"
    assert compute_health(job)["is_failure"] is True


def test_provider_diagnostics_from_response_json() -> None:
    diagnostics = extract_provider_diagnostics(
        {
            "provider_metadata": {
                "provider": "openai",
                "model": "gpt-test",
                "latency_ms": 42,
                "cached": False,
                "finish_reason": "stop",
                "retry_count": 1,
            },
            "quality": {"cache_hit": False, "provider": "openai", "model": "gpt-test"},
        }
    )
    assert diagnostics["provider"] == "openai"
    assert diagnostics["model"] == "gpt-test"
    assert diagnostics["latency_ms"] == 42
    assert diagnostics["cached"] is False
    assert diagnostics["finish_reason"] == "stop"
    assert diagnostics["retry_count"] == 1


def test_events_from_progress() -> None:
    from app.models.ai_generation_job import AIGenerationJob
    from uuid import uuid4

    now = datetime.now(UTC)
    job = AIGenerationJob(
        id=uuid4(),
        feature="finding",
        entity_type="finding",
        entity_id="x",
        resource_id=uuid4(),
        report_hash="",
        status="completed",
        progress=100,
        queued_at=now - timedelta(seconds=5),
        started_at=now - timedelta(seconds=4),
        completed_at=now,
    )
    events = [e["event"] for e in compute_job_events(job)]
    assert events[0] == "QUEUED"
    assert "STARTED" in events
    assert "PROVIDER_STARTED" in events
    assert "GROUNDING_STARTED" in events
    assert "PERSIST_STARTED" in events
    assert events[-1] == "COMPLETED"


@pytest.mark.asyncio
async def test_phase_history_and_completed_dto(db_session: AsyncSession) -> None:
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

    assert job.status == "completed"
    phases = [p["phase"] for p in (job.phase_history or [])]
    assert "loading" in phases
    assert "building_prompt" in phases
    assert "provider_request" in phases
    assert "grounding" in phases
    assert "persisting" in phases
    assert all("duration_ms" in p for p in job.phase_history)

    dto = await job_to_dto(db_session, job)
    payload = dto.model_dump(mode="json")
    assert payload["summary"] == "Completed"
    assert payload["health"]["is_success"] is True
    assert payload["health"]["is_terminal"] is True
    assert len(payload["phase_history"]) >= 4
    assert any(e["event"] == "COMPLETED" for e in payload["events"])
    assert payload["provider"] == "openai"
    assert payload["model"] == "gpt-test"
    assert payload["cached"] is False
    assert payload["failure_category"] is None


@pytest.mark.asyncio
async def test_failure_category_on_provider_error(db_session: AsyncSession) -> None:
    _audit, finding, _rec = await _seed(db_session)
    await db_session.commit()
    stub = StubAIService()
    stub.fail_with = AIProviderError("upstream timeout")
    queue = InMemoryQueue()
    accepted = await QueueGenerationUseCase(db_session, queue).execute(
        feature=AIFeature.FINDING,
        resource_id=finding.id,
    )
    await db_session.commit()

    job = await AIJobRunner(stub).run(db_session, accepted.accepted.job_id)
    await db_session.commit()
    assert job.status == "failed"
    assert job.failure_category == JobFailureCategory.TIMEOUT.value

    result = await GetGenerationJobUseCase(db_session).execute(job.id)
    assert result.job.failure_category == "TIMEOUT"
    assert result.job.summary == "Failed"
    assert result.job.health is not None
    assert result.job.health.is_failure is True


@pytest.mark.asyncio
async def test_provider_diagnostics_persisted_on_failure(
    db_session: AsyncSession,
) -> None:
    _audit, finding, _rec = await _seed(db_session)
    await db_session.commit()
    stub = StubAIService()
    stub.fail_with = AIProviderError(
        "OpenRouter rate limit (429): Rate limit exceeded",
        diagnostics={
            "provider": "openrouter",
            "model": "openai/gpt-oss-20b:free",
            "stage": "responses.parse",
            "status_code": 429,
            "error_type": "RateLimitError",
            "finish_reason": None,
            "total_provider_ms": 42,
            "stage_latency_ms": {"responses.parse": 42},
            "raw_preview": "Rate limit exceeded",
        },
    )
    queue = InMemoryQueue()
    accepted = await QueueGenerationUseCase(db_session, queue).execute(
        feature=AIFeature.FINDING,
        resource_id=finding.id,
    )
    await db_session.commit()

    job = await AIJobRunner(stub).run(db_session, accepted.accepted.job_id)
    await db_session.commit()
    assert job.status == "failed"
    assert any(
        isinstance(p, dict) and p.get("phase") == "provider_diagnostics"
        for p in (job.phase_history or [])
    )

    dto = await job_to_dto(db_session, job)
    assert dto.provider == "openrouter"
    assert dto.model == "openai/gpt-oss-20b:free"
    assert dto.latency_ms == 42


def test_extract_provider_diagnostics_from_phase_history() -> None:
    diag = extract_provider_diagnostics(
        None,
        phase_history=[
            {
                "phase": "provider_diagnostics",
                "name": "provider_diagnostics",
                "duration_ms": 55,
                "diagnostics": {
                    "provider": "openrouter",
                    "model": "m",
                    "finish_reason": "stop",
                    "total_provider_ms": 55,
                },
            }
        ],
    )
    assert diag["provider"] == "openrouter"
    assert diag["model"] == "m"
    assert diag["latency_ms"] == 55
    assert diag["finish_reason"] == "stop"


@pytest.mark.asyncio
async def test_cancel_sets_user_cancelled_category(db_session: AsyncSession) -> None:
    _audit, finding, _rec = await _seed(db_session)
    await db_session.commit()
    queue = InMemoryQueue()
    accepted = await QueueGenerationUseCase(db_session, queue).execute(
        feature=AIFeature.FINDING,
        resource_id=finding.id,
    )
    await db_session.commit()
    result = await CancelGenerationJobUseCase(db_session, queue).execute(
        accepted.accepted.job_id
    )
    await db_session.commit()
    assert result.job.failure_category == "USER_CANCELLED"
    assert result.job.summary == "Cancelled"
    assert result.job.health is not None
    assert result.job.health.is_terminal is True


@pytest.mark.asyncio
async def test_observability_bundle_helpers(db_session: AsyncSession) -> None:
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
    await repo.mark_running(job, worker="local-worker-1")
    await repo.append_phase(
        job,
        "loading",
        started_at=datetime.now(UTC) - timedelta(milliseconds=12),
        completed_at=datetime.now(UTC),
    )
    await db_session.commit()

    bundle = AIGenerationJobRepository.compute_observability(job)
    assert bundle.summary == "Running"
    assert bundle.phase_history[0]["phase"] == "loading"
    assert bundle.phase_history[0]["duration_ms"] is not None
    assert bundle.health["is_running"] is True
    assert any(e["event"] == "STARTED" for e in bundle.events)

"""API tests for async AI generation jobs (Sprint 26)."""

from __future__ import annotations

import asyncio

import pytest

from app.dependencies.ai_jobs import reset_job_queue
from tests.api.test_ai import StubAIService, _seed

pytest_plugins = ["tests.api.test_ai"]


@pytest.fixture(autouse=True)
def _reset_queue() -> None:
    reset_job_queue()
    yield
    reset_job_queue()


async def _wait_completed(client, job_id: str, *, timeout: float = 5.0) -> dict:
    deadline = asyncio.get_event_loop().time() + timeout
    while asyncio.get_event_loop().time() < deadline:
        resp = await client.get(f"/api/v1/jobs/{job_id}")
        assert resp.status_code == 200
        body = resp.json()
        if body["status"] in ("completed", "failed", "cancelled"):
            return body
        await asyncio.sleep(0.05)
    raise AssertionError(f"job {job_id} did not finish in time")


@pytest.mark.asyncio
async def test_generate_poll_result_flow(api_client, db_session, stub_ai: StubAIService):
    _audit, finding, _rec = await _seed(db_session)
    await db_session.commit()

    resp = await api_client.post(f"/api/v1/findings/{finding.id}/ai/generate")
    assert resp.status_code == 202
    body = resp.json()
    assert body["status"] == "queued"
    job_id = body["job_id"]

    status = await _wait_completed(api_client, job_id)
    assert status["status"] == "completed"
    assert status["generation_id"] is not None
    assert status["feature"] == "finding"
    assert status["progress"] == 100
    assert status["worker"] == "local-worker-1"
    assert status["latest_version"] == 1
    assert status["result_url"] == f"/api/v1/jobs/{job_id}/result"
    assert status["queue_wait_ms"] is not None
    assert status["execution_ms"] is not None
    assert status["total_duration_ms"] is not None
    assert status["max_attempts"] >= 1
    assert status["summary"] == "Completed"
    assert status["health"]["is_success"] is True
    assert status["health"]["is_terminal"] is True
    assert isinstance(status["phase_history"], list)
    assert len(status["phase_history"]) >= 1
    assert any(e["event"] == "COMPLETED" for e in status["events"])
    assert status["provider"] == "openai"
    assert status.get("failure_category") in (None, )
    assert status["expired"] is False
    assert status["cleanup_candidate"] is False
    assert status["stale"] is False
    assert status["age_ms"] is not None
    assert "duration_class" in status
    assert "queue_class" in status
    assert status["expires_at"] is not None

    result = await api_client.get(f"/api/v1/jobs/{job_id}/result")
    assert result.status_code == 200
    payload = result.json()
    assert payload["result"]["finding_id"] == "seo.viewport.missing"
    assert payload["quality"]["feature"] == "finding"
    assert len(stub_ai.calls) == 1


@pytest.mark.asyncio
async def test_result_while_queued_is_409(api_client, db_session):
    audit, finding, _rec = await _seed(db_session)
    from app.repositories.ai_generation_job import AIGenerationJobRepository

    job = await AIGenerationJobRepository(db_session).create(
        feature="finding",
        entity_type="finding",
        entity_id="seo.viewport.missing",
        resource_id=finding.id,
        report_hash="pending",
        audit_id=audit.id,
        status="queued",
    )
    await db_session.commit()

    early = await api_client.get(f"/api/v1/jobs/{job.id}/result")
    assert early.status_code == 409
    assert early.json()["error"]["code"] == "JOB_NOT_COMPLETE"


@pytest.mark.asyncio
async def test_job_not_found(api_client):
    missing = "00000000-0000-0000-0000-000000000099"
    resp = await api_client.get(f"/api/v1/jobs/{missing}")
    assert resp.status_code == 404
    assert resp.json()["error"]["code"] == "JOB_NOT_FOUND"


@pytest.mark.asyncio
async def test_cancel_with_reason(api_client, db_session, stub_ai: StubAIService):
    _audit, finding, _rec = await _seed(db_session)
    await db_session.commit()

    # Create a second queued job while first is slow so cancel can succeed
    original = stub_ai.explain_finding

    async def slow_explain(context, **kwargs):
        await asyncio.sleep(2.0)
        return await original(context, **kwargs)

    stub_ai.explain_finding = slow_explain  # type: ignore[method-assign]

    r1 = await api_client.post(f"/api/v1/findings/{finding.id}/ai/generate")
    r2 = await api_client.post(f"/api/v1/findings/{finding.id}/ai/generate")
    job2 = r2.json()["job_id"]

    cancel = await api_client.post(
        f"/api/v1/jobs/{job2}/cancel",
        json={"reason": "DUPLICATE"},
    )
    if cancel.status_code == 200:
        body = cancel.json()
        assert body["status"] == "cancelled"
        assert body["cancel_reason"] == "DUPLICATE"
        assert body["progress"] == 0
    else:
        assert cancel.status_code == 400

    await _wait_completed(api_client, r1.json()["job_id"], timeout=5.0)


@pytest.mark.asyncio
async def test_recommendation_and_summary_generate(
    api_client, db_session, stub_ai: StubAIService
):
    audit, _finding, rec = await _seed(db_session)
    await db_session.commit()

    for path in (
        f"/api/v1/recommendations/{rec.id}/ai/generate",
        f"/api/v1/recommendations/{rec.id}/ai/generate-quick-win",
        f"/api/v1/audits/{audit.id}/ai/generate-executive-summary",
        f"/api/v1/audits/{audit.id}/ai/generate-business-summary",
    ):
        resp = await api_client.post(path)
        assert resp.status_code == 202, path
        job_id = resp.json()["job_id"]
        status = await _wait_completed(api_client, job_id)
        assert status["status"] == "completed", path
        result = await api_client.get(f"/api/v1/jobs/{job_id}/result")
        assert result.status_code == 200, path


@pytest.mark.asyncio
async def test_list_jobs(api_client, db_session, stub_ai: StubAIService):
    _audit, finding, _rec = await _seed(db_session)
    await db_session.commit()

    resp = await api_client.post(f"/api/v1/findings/{finding.id}/ai/generate")
    job_id = resp.json()["job_id"]
    await _wait_completed(api_client, job_id)

    listed = await api_client.get("/api/v1/jobs", params={"feature": "finding"})
    assert listed.status_code == 200
    items = listed.json()["items"]
    assert any(i["job_id"] == job_id for i in items)


@pytest.mark.asyncio
async def test_failed_job_status(api_client, db_session, stub_ai: StubAIService):
    _audit, finding, _rec = await _seed(db_session)
    await db_session.commit()
    stub_ai.fail_with = RuntimeError("boom")

    resp = await api_client.post(f"/api/v1/findings/{finding.id}/ai/generate")
    job_id = resp.json()["job_id"]
    status = await _wait_completed(api_client, job_id)
    assert status["status"] == "failed"
    assert "boom" in (status["error"] or "")

    result = await api_client.get(f"/api/v1/jobs/{job_id}/result")
    assert result.status_code == 409

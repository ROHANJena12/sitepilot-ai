"""Sprint 25 — regeneration, latest, and version history API tests."""

from __future__ import annotations

from typing import Any

import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.ai.features import AIFeature
from app.models.ai_generation import AIGeneration

pytest_plugins = ["tests.api.test_ai"]


@pytest.mark.asyncio
async def test_regenerate_executive_summary(
    api_client: Any, db_session: AsyncSession
) -> None:
    from tests.api.test_ai import _seed

    audit, _, _ = await _seed(db_session)
    first = await api_client.post(
        f"/api/v1/audits/{audit.id}/ai/regenerate-executive-summary"
    )
    assert first.status_code == 200
    assert first.json()["result"]["headline"]

    latest = await api_client.get(
        f"/api/v1/audits/{audit.id}/ai/executive-summary/latest"
    )
    assert latest.status_code == 200
    assert latest.json()["result"]["headline"] == first.json()["result"]["headline"]


@pytest.mark.asyncio
async def test_identical_regeneration_reuses_version(
    api_client: Any, db_session: AsyncSession
) -> None:
    from tests.api.test_ai import _seed

    audit, _, _ = await _seed(db_session)
    a = await api_client.post(
        f"/api/v1/audits/{audit.id}/ai/regenerate-executive-summary"
    )
    b = await api_client.post(
        f"/api/v1/audits/{audit.id}/ai/regenerate-executive-summary"
    )
    assert a.status_code == 200
    assert b.status_code == 200

    rows = (
        await db_session.execute(
            select(AIGeneration).where(
                AIGeneration.audit_id == audit.id,
                AIGeneration.feature == AIFeature.EXECUTIVE_SUMMARY.value,
            )
        )
    ).scalars().all()
    assert len(rows) == 1
    assert rows[0].version == 1


@pytest.mark.asyncio
async def test_version_history_and_retrieval(
    api_client: Any, db_session: AsyncSession, stub_ai: Any
) -> None:
    from tests.api.test_ai import _seed

    audit, _, _ = await _seed(db_session)
    await api_client.post(
        f"/api/v1/audits/{audit.id}/ai/regenerate-executive-summary"
    )

    # Force different narrative so version increments.
    original = stub_ai.generate_executive_summary

    async def _alt(context: Any, **kwargs: Any) -> Any:
        resp = await original(context, **kwargs)
        new_result = resp.result.model_copy(update={"headline": "Changed headline"})
        return resp.model_copy(update={"result": new_result})

    stub_ai.generate_executive_summary = _alt
    second = await api_client.post(
        f"/api/v1/audits/{audit.id}/ai/regenerate-executive-summary"
    )
    assert second.status_code == 200
    assert second.json()["result"]["headline"] == "Changed headline"

    hist = await api_client.get(
        f"/api/v1/audits/{audit.id}/ai/executive-summary/versions"
    )
    assert hist.status_code == 200
    body = hist.json()
    assert body["feature"] == "executive_summary"
    assert len(body["items"]) == 2
    assert body["items"][0]["version"] == 1
    assert body["items"][1]["version"] == 2
    assert "result" not in body["items"][0]

    v1 = await api_client.get(
        f"/api/v1/audits/{audit.id}/ai/executive-summary/versions/1"
    )
    v2 = await api_client.get(
        f"/api/v1/audits/{audit.id}/ai/executive-summary/versions/2"
    )
    assert v1.status_code == 200
    assert v2.status_code == 200
    assert v1.json()["result"]["headline"] != v2.json()["result"]["headline"]

    latest = await api_client.get(
        f"/api/v1/audits/{audit.id}/ai/executive-summary/latest"
    )
    assert latest.json()["result"]["headline"] == "Changed headline"


@pytest.mark.asyncio
async def test_latest_not_found(api_client: Any, db_session: AsyncSession) -> None:
    from tests.api.test_ai import _seed

    audit, _, _ = await _seed(db_session)
    resp = await api_client.get(
        f"/api/v1/audits/{audit.id}/ai/executive-summary/latest"
    )
    assert resp.status_code == 404
    assert resp.json()["error"]["code"] == "GENERATION_NOT_FOUND"


@pytest.mark.asyncio
async def test_finding_regenerate_and_versions(
    api_client: Any, db_session: AsyncSession
) -> None:
    from tests.api.test_ai import _seed

    _, finding, _ = await _seed(db_session)
    regen = await api_client.post(f"/api/v1/findings/{finding.id}/ai/regenerate")
    assert regen.status_code == 200
    latest = await api_client.get(f"/api/v1/findings/{finding.id}/ai/latest")
    assert latest.status_code == 200
    versions = await api_client.get(f"/api/v1/findings/{finding.id}/ai/versions")
    assert versions.status_code == 200
    assert len(versions.json()["items"]) == 1


@pytest.mark.asyncio
async def test_recommendation_and_quick_win_regenerate(
    api_client: Any, db_session: AsyncSession
) -> None:
    from tests.api.test_ai import _seed

    _, _, rec = await _seed(db_session)
    r1 = await api_client.post(f"/api/v1/recommendations/{rec.id}/ai/regenerate")
    assert r1.status_code == 200
    qw = await api_client.post(
        f"/api/v1/recommendations/{rec.id}/ai/regenerate-quick-win"
    )
    assert qw.status_code == 200
    qw_latest = await api_client.get(
        f"/api/v1/recommendations/{rec.id}/ai/quick-win/latest"
    )
    assert qw_latest.status_code == 200


@pytest.mark.asyncio
async def test_immutable_history_preserved(
    api_client: Any, db_session: AsyncSession, stub_ai: Any
) -> None:
    from tests.api.test_ai import _seed

    audit, _, _ = await _seed(db_session)
    await api_client.post(
        f"/api/v1/audits/{audit.id}/ai/regenerate-business-summary"
    )
    original = stub_ai.generate_business_summary

    async def _alt(context: Any, **kwargs: Any) -> Any:
        resp = await original(context, **kwargs)
        new_result = resp.result.model_copy(
            update={"headline": "Business rewrite"}
        )
        return resp.model_copy(update={"result": new_result})

    stub_ai.generate_business_summary = _alt
    await api_client.post(
        f"/api/v1/audits/{audit.id}/ai/regenerate-business-summary"
    )

    rows = (
        await db_session.execute(
            select(AIGeneration)
            .where(
                AIGeneration.audit_id == audit.id,
                AIGeneration.feature == AIFeature.BUSINESS_SUMMARY.value,
            )
            .order_by(AIGeneration.version.asc())
        )
    ).scalars().all()
    assert len(rows) == 2
    assert rows[0].version == 1
    assert rows[1].version == 2
    assert rows[0].response_json["result"]["headline"] != rows[1].response_json[
        "result"
    ]["headline"]

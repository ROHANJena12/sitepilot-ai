"""API-level AI persistence tests (Sprint 24)."""

from __future__ import annotations

from typing import Any

import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.ai.features import AIFeature
from app.application.ai.persist import AIGenerationPersister
from app.models.ai_generation import AIGeneration

# Reuse fixtures + seed from Sprint 23 API tests.
pytest_plugins = ["tests.api.test_ai"]


@pytest.mark.asyncio
async def test_api_persists_generation(
    api_client: Any,
    db_session: AsyncSession,
) -> None:
    from tests.api.test_ai import _seed

    audit, _, _ = await _seed(db_session)
    resp = await api_client.get(f"/api/v1/audits/{audit.id}/ai/executive-summary")
    assert resp.status_code == 200
    body = resp.json()
    assert body["result"]["headline"]

    rows = (
        await db_session.execute(
            select(AIGeneration).where(
                AIGeneration.audit_id == audit.id,
                AIGeneration.feature == AIFeature.EXECUTIVE_SUMMARY.value,
            )
        )
    ).scalars().all()
    assert len(rows) == 1
    assert rows[0].response_hash
    assert rows[0].report_hash
    assert rows[0].version == 1
    assert rows[0].response_json["result"]["headline"] == body["result"]["headline"]


@pytest.mark.asyncio
async def test_api_identical_response_reuses_version(
    api_client: Any,
    db_session: AsyncSession,
) -> None:
    from tests.api.test_ai import _seed

    audit, _, _ = await _seed(db_session)
    first = await api_client.get(f"/api/v1/audits/{audit.id}/ai/executive-summary")
    second = await api_client.get(f"/api/v1/audits/{audit.id}/ai/executive-summary")
    assert first.status_code == 200
    assert second.status_code == 200

    rows = (
        await db_session.execute(
            select(AIGeneration).where(
                AIGeneration.audit_id == audit.id,
                AIGeneration.feature == AIFeature.EXECUTIVE_SUMMARY.value,
            )
        )
    ).scalars().all()
    # Stub returns identical content → single immutable version reused.
    assert len(rows) == 1
    assert rows[0].version == 1


@pytest.mark.asyncio
async def test_api_succeeds_when_persist_returns_none(
    api_client: Any,
    db_session: AsyncSession,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from tests.api.test_ai import _seed

    audit, _, _ = await _seed(db_session)

    async def _none_persist(self: Any, *args: Any, **kwargs: Any) -> None:  # noqa: ANN401
        return None

    monkeypatch.setattr(AIGenerationPersister, "persist", _none_persist)
    resp = await api_client.get(f"/api/v1/audits/{audit.id}/ai/executive-summary")
    assert resp.status_code == 200
    assert resp.json()["generation_id"]

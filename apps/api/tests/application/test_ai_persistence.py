"""Tests for AI generation persistence, hashing, and versioning (Sprint 24)."""

from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path
from typing import Any
from unittest.mock import AsyncMock
from uuid import uuid4

import pytest
from alembic.script import ScriptDirectory
from sqlalchemy.ext.asyncio import AsyncSession

from app.ai.entity_types import AIEntityType
from app.ai.features import AIFeature
from app.ai.response import AIQualityMetadata, AIResponse, ProviderResponseMetadata
from app.ai.schemas import ExecutiveSummary
from app.ai.telemetry import GenerationTelemetry
from app.application.ai.persist import AIGenerationPersister
from app.application.ai.response_hash import (
    canonical_ai_response_payload,
    hash_ai_response,
)
from app.domain.audit_status import AuditStatus
from app.models.audit_run import AuditRun
from app.repositories.ai_generation import AIGenerationRepository
from app.repositories.organization import OrganizationRepository
from app.repositories.project import ProjectRepository
from app.repositories.website import WebsiteRepository
from app.schemas.organization import OrganizationCreate
from app.schemas.project import ProjectCreate
from app.schemas.website import WebsiteCreate


def _meta(*, cached: bool = False) -> ProviderResponseMetadata:
    return ProviderResponseMetadata(
        generation_id=uuid4(),
        feature=AIFeature.EXECUTIVE_SUMMARY,
        provider="openai",
        model="gpt-test",
        cached=cached,
        retry_count=0,
    )


def _ai_response(
    *,
    headline: str = "H",
    generation_id: Any = None,
    cached: bool = False,
) -> AIResponse[ExecutiveSummary]:
    gid = generation_id or uuid4()
    return AIResponse(
        result=ExecutiveSummary(
            headline=headline,
            summary="S",
            key_risks=["r"],
            priority_actions=["a"],
        ),
        generation_id=gid,
        quality=AIQualityMetadata(
            grounded=True,
            validation_passed=True,
            cache_hit=cached,
            provider="openai",
            model="gpt-test",
            prompt_version="v1",
            builder_version=1,
            schema_version="ai.executive_summary.v3",
            prompt_hash="phash",
            feature=AIFeature.EXECUTIVE_SUMMARY,
        ),
        provider_metadata=_meta(cached=cached).model_copy(
            update={"generation_id": gid}
        ),
        telemetry=GenerationTelemetry(
            generation_id=gid,
            feature=AIFeature.EXECUTIVE_SUMMARY,
            provider="openai",
            model="gpt-test",
            prompt_version="v1",
            schema_version="ai.executive_summary.v3",
            builder_version=1,
            cache_hit=cached,
            status="cached" if cached else "success",
            created_at=datetime.now(UTC),
        ),
        session_id=uuid4(),
        generated_at=datetime.now(UTC),
    )


def test_response_hash_excludes_volatile_fields() -> None:
    a = _ai_response(headline="Same")
    b = _ai_response(headline="Same", generation_id=uuid4())
    assert hash_ai_response(a) == hash_ai_response(b)
    payload = canonical_ai_response_payload(a)
    assert "generation_id" not in payload
    assert "generated_at" not in payload
    assert "created_at" not in (payload.get("telemetry") or {})


def test_response_hash_changes_when_content_changes() -> None:
    a = _ai_response(headline="One")
    b = _ai_response(headline="Two")
    assert hash_ai_response(a) != hash_ai_response(b)


def test_migration_revision_chain() -> None:
    root = Path(__file__).resolve().parents[2]
    script = ScriptDirectory(str(root / "alembic"))
    assert script.get_heads() == ["202607121900_011"]
    rev = script.get_revision("202607121900_011")
    assert rev is not None
    assert rev.down_revision == "202607121800_010"


async def _seed_audit(session: AsyncSession) -> AuditRun:
    org = await OrganizationRepository(session).create(
        OrganizationCreate(name="AI Persist Org", slug=f"ai-p-{uuid4().hex[:8]}")
    )
    project = await ProjectRepository(session).create(
        ProjectCreate(
            organization_id=org.id,
            name="AI Persist Project",
            slug=f"ai-pp-{uuid4().hex[:8]}",
        )
    )
    website = await WebsiteRepository(session).create(
        WebsiteCreate(project_id=project.id, url="https://ai-persist.example")
    )
    now = datetime.now(UTC)
    audit = AuditRun(
        website_id=website.id,
        organization_id=org.id,
        project_id=project.id,
        requested_url="https://ai-persist.example/",
        canonical_url="https://ai-persist.example/",
        status=AuditStatus.COMPLETE.value,
        progress_percent=100,
        started_at=now,
        completed_at=now,
        duration_ms=1000,
        health_score=90,
        engine_versions={},
        pipeline_metadata={},
    )
    session.add(audit)
    await session.flush()
    return audit


@pytest.mark.asyncio
async def test_repository_create_get_latest_list_exists(
    db_session: AsyncSession,
) -> None:
    audit = await _seed_audit(db_session)
    repo = AIGenerationRepository(db_session)
    response = _ai_response()
    rh = hash_ai_response(response)

    row = await repo.create(
        generation_id=response.generation_id,
        feature=AIFeature.EXECUTIVE_SUMMARY,
        entity_type=AIEntityType.EXECUTIVE_SUMMARY,
        entity_id=str(audit.id),
        audit_id=audit.id,
        provider="openai",
        model="gpt-test",
        schema_version="ai.executive_summary.v3",
        builder_version=1,
        prompt_version="v1",
        prompt_hash="phash",
        report_hash="rh-1",
        input_hash="ih-1",
        response_hash=rh,
        locale="en",
        response_json=response.model_dump(mode="json"),
        telemetry_json=None,
        diagnostics_json=None,
        status="success",
        version=1,
    )
    await db_session.commit()

    loaded = await repo.get(row.id)
    assert loaded is not None
    assert loaded.response_hash == rh
    assert loaded.report_hash == "rh-1"

    latest = await repo.get_latest(
        feature=AIFeature.EXECUTIVE_SUMMARY,
        entity_id=str(audit.id),
        report_hash="rh-1",
    )
    assert latest is not None
    assert latest.id == row.id

    versions = await repo.list_versions(
        feature=AIFeature.EXECUTIVE_SUMMARY,
        entity_id=str(audit.id),
        report_hash="rh-1",
    )
    assert len(versions) == 1
    assert await repo.exists(
        feature=AIFeature.EXECUTIVE_SUMMARY,
        entity_id=str(audit.id),
        report_hash="rh-1",
        version=1,
    )


@pytest.mark.asyncio
async def test_create_or_reuse_identical_content(
    db_session: AsyncSession,
) -> None:
    audit = await _seed_audit(db_session)
    repo = AIGenerationRepository(db_session)
    response = _ai_response(headline="Stable")
    common = dict(
        generation_id=response.generation_id,
        feature=AIFeature.EXECUTIVE_SUMMARY,
        entity_type=AIEntityType.EXECUTIVE_SUMMARY,
        entity_id=str(audit.id),
        audit_id=audit.id,
        provider="openai",
        model="gpt-test",
        schema_version="ai.executive_summary.v3",
        builder_version=1,
        prompt_version="v1",
        prompt_hash="phash",
        report_hash="rh-same",
        input_hash="ih",
        response_hash=hash_ai_response(response),
        locale="en",
        response_json=response.model_dump(mode="json"),
        telemetry_json=None,
        diagnostics_json=None,
        status="success",
    )
    first = await repo.create_or_reuse(**common)
    second = await repo.create_or_reuse(**common)
    await db_session.commit()
    assert first.id == second.id
    assert first.version == 1
    versions = await repo.list_versions(
        feature=AIFeature.EXECUTIVE_SUMMARY,
        entity_id=str(audit.id),
        report_hash="rh-same",
    )
    assert len(versions) == 1


@pytest.mark.asyncio
async def test_version_increments_when_content_changes(
    db_session: AsyncSession,
) -> None:
    audit = await _seed_audit(db_session)
    repo = AIGenerationRepository(db_session)
    r1 = _ai_response(headline="V1")
    r2 = _ai_response(headline="V2")
    base = dict(
        feature=AIFeature.EXECUTIVE_SUMMARY,
        entity_type=AIEntityType.EXECUTIVE_SUMMARY,
        entity_id=str(audit.id),
        audit_id=audit.id,
        provider="openai",
        model="gpt-test",
        schema_version="ai.executive_summary.v3",
        builder_version=1,
        prompt_version="v1",
        prompt_hash="phash",
        report_hash="rh-ver",
        input_hash="ih",
        locale="en",
        telemetry_json=None,
        diagnostics_json=None,
        status="success",
    )
    first = await repo.create_or_reuse(
        **base,
        generation_id=r1.generation_id,
        response_hash=hash_ai_response(r1),
        response_json=r1.model_dump(mode="json"),
    )
    second = await repo.create_or_reuse(
        **base,
        generation_id=r2.generation_id,
        response_hash=hash_ai_response(r2),
        response_json=r2.model_dump(mode="json"),
    )
    await db_session.commit()
    assert first.version == 1
    assert second.version == 2
    assert first.id != second.id
    reloaded = await repo.get(first.id)
    assert reloaded is not None
    assert reloaded.version == 1
    assert reloaded.response_hash == hash_ai_response(r1)


@pytest.mark.asyncio
async def test_persister_writes_row(db_session: AsyncSession) -> None:
    audit = await _seed_audit(db_session)
    response = _ai_response()
    persister = AIGenerationPersister(db_session)
    row = await persister.persist(
        response,
        feature=AIFeature.EXECUTIVE_SUMMARY,
        entity_type=AIEntityType.EXECUTIVE_SUMMARY,
        entity_id=str(audit.id),
        audit_id=audit.id,
        report_hash="rh-persist",
    )
    await db_session.commit()
    assert row is not None
    assert row.response_hash == hash_ai_response(response)
    assert row.report_hash == "rh-persist"
    assert row.status == "success"


@pytest.mark.asyncio
async def test_persister_best_effort_on_failure(db_session: AsyncSession) -> None:
    audit = await _seed_audit(db_session)
    persister = AIGenerationPersister(db_session)
    persister._repo.create_or_reuse = AsyncMock(  # type: ignore[method-assign]
        side_effect=RuntimeError("db down")
    )
    response = _ai_response()
    result = await persister.persist(
        response,
        feature=AIFeature.EXECUTIVE_SUMMARY,
        entity_id=str(audit.id),
        audit_id=audit.id,
        report_hash="rh-fail",
    )
    assert result is None

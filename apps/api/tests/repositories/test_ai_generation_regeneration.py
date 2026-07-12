"""Repository tests for Sprint 25 regeneration aliases."""

from __future__ import annotations

from datetime import UTC, datetime
from uuid import uuid4

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.ai.entity_types import AIEntityType
from app.ai.features import AIFeature
from app.ai.response import AIQualityMetadata, AIResponse, ProviderResponseMetadata
from app.ai.schemas import ExecutiveSummary
from app.application.ai.response_hash import hash_ai_response
from app.domain.audit_status import AuditStatus
from app.models.audit_run import AuditRun
from app.repositories.ai_generation import AIGenerationRepository
from app.repositories.organization import OrganizationRepository
from app.repositories.project import ProjectRepository
from app.repositories.website import WebsiteRepository
from app.schemas.organization import OrganizationCreate
from app.schemas.project import ProjectCreate
from app.schemas.website import WebsiteCreate


def _response(headline: str = "H") -> AIResponse[ExecutiveSummary]:
    gid = uuid4()
    return AIResponse(
        result=ExecutiveSummary(headline=headline, summary="S"),
        generation_id=gid,
        quality=AIQualityMetadata(
            grounded=True,
            validation_passed=True,
            cache_hit=False,
            provider="openai",
            model="gpt-test",
            prompt_version="v1",
            builder_version=1,
            schema_version="ai.executive_summary.v3",
            feature=AIFeature.EXECUTIVE_SUMMARY,
        ),
        provider_metadata=ProviderResponseMetadata(
            generation_id=gid,
            feature=AIFeature.EXECUTIVE_SUMMARY,
            provider="openai",
            model="gpt-test",
            cached=False,
            retry_count=0,
        ),
        session_id=uuid4(),
        generated_at=datetime.now(UTC),
    )


async def _audit(session: AsyncSession) -> AuditRun:
    org = await OrganizationRepository(session).create(
        OrganizationCreate(name="Regen Org", slug=f"rg-{uuid4().hex[:8]}")
    )
    project = await ProjectRepository(session).create(
        ProjectCreate(
            organization_id=org.id,
            name="Regen Project",
            slug=f"rgp-{uuid4().hex[:8]}",
        )
    )
    website = await WebsiteRepository(session).create(
        WebsiteCreate(project_id=project.id, url="https://regen.example")
    )
    now = datetime.now(UTC)
    audit = AuditRun(
        website_id=website.id,
        organization_id=org.id,
        project_id=project.id,
        requested_url="https://regen.example/",
        canonical_url="https://regen.example/",
        status=AuditStatus.COMPLETE.value,
        progress_percent=100,
        started_at=now,
        completed_at=now,
        duration_ms=1,
        health_score=90,
        engine_versions={},
        pipeline_metadata={},
    )
    session.add(audit)
    await session.flush()
    return audit


@pytest.mark.asyncio
async def test_repo_regenerate_latest_get_version(db_session: AsyncSession) -> None:
    audit = await _audit(db_session)
    repo = AIGenerationRepository(db_session)
    r1 = _response("One")
    r2 = _response("Two")
    common = dict(
        feature=AIFeature.EXECUTIVE_SUMMARY,
        entity_type=AIEntityType.EXECUTIVE_SUMMARY,
        entity_id=str(audit.id),
        audit_id=audit.id,
        provider="openai",
        model="gpt-test",
        schema_version="ai.executive_summary.v3",
        builder_version=1,
        prompt_version="v1",
        prompt_hash="p",
        report_hash="rh",
        input_hash="i",
        locale="en",
        telemetry_json=None,
        diagnostics_json=None,
        status="success",
    )
    first = await repo.regenerate(
        **common,
        generation_id=r1.generation_id,
        response_hash=hash_ai_response(r1),
        response_json=r1.model_dump(mode="json"),
    )
    same = await repo.regenerate(
        **common,
        generation_id=r1.generation_id,
        response_hash=hash_ai_response(r1),
        response_json=r1.model_dump(mode="json"),
    )
    second = await repo.regenerate(
        **common,
        generation_id=r2.generation_id,
        response_hash=hash_ai_response(r2),
        response_json=r2.model_dump(mode="json"),
    )
    await db_session.commit()

    assert first.id == same.id
    assert first.version == 1
    assert second.version == 2

    latest = await repo.latest(
        feature=AIFeature.EXECUTIVE_SUMMARY,
        entity_id=str(audit.id),
        report_hash="rh",
    )
    assert latest is not None
    assert latest.version == 2

    versions = await repo.get_versions(
        feature=AIFeature.EXECUTIVE_SUMMARY,
        entity_id=str(audit.id),
        report_hash="rh",
    )
    assert [v.version for v in versions] == [1, 2]

    v1 = await repo.get_version(
        feature=AIFeature.EXECUTIVE_SUMMARY,
        entity_id=str(audit.id),
        report_hash="rh",
        version=1,
    )
    assert v1 is not None
    assert v1.response_json["result"]["headline"] == "One"

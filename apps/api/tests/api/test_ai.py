"""API tests for Sprint 23 AI explanation endpoints."""

from __future__ import annotations

from collections.abc import AsyncIterator
from datetime import UTC, datetime
from typing import Any
from uuid import UUID, uuid4

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, async_sessionmaker

from app.ai.exceptions import (
    AIConfigurationError,
    AIProviderError,
    InvalidAIResponse,
)
from app.ai.features import AIFeature
from app.ai.response import AIQualityMetadata, AIResponse, ProviderResponseMetadata
from app.ai.schemas import (
    BusinessSummary,
    ExecutiveSummary,
    FindingExplanation,
    QuickWinExplanation,
    RecommendationExplanation,
)
from app.ai.service import AIService
from app.ai.telemetry import GenerationTelemetry
from app.core.config import Settings, clear_settings_cache
from app.dependencies.ai import get_ai_service
from app.dependencies.db import get_db_session
from app.domain.audit_status import AuditStatus
from app.main import create_app
from app.models.audit_finding import AuditFinding
from app.models.audit_run import AuditRun
from app.models.health_score import HealthScore
from app.models.recommendation import RecommendationRow
from app.repositories.organization import OrganizationRepository
from app.repositories.project import ProjectRepository
from app.repositories.website import WebsiteRepository
from app.schemas.organization import OrganizationCreate
from app.schemas.project import ProjectCreate
from app.schemas.website import WebsiteCreate


def _meta(*, cached: bool = False, feature: AIFeature = AIFeature.FINDING) -> ProviderResponseMetadata:
    return ProviderResponseMetadata(
        generation_id=uuid4(),
        feature=feature,
        provider="openai",
        model="gpt-test",
        latency_ms=12,
        tokens_in=10,
        tokens_out=20,
        total_tokens=30,
        cached=cached,
        retry_count=0,
    )


def _quality(*, cache_hit: bool = False, feature: AIFeature = AIFeature.FINDING) -> AIQualityMetadata:
    return AIQualityMetadata(
        grounded=True,
        validation_passed=True,
        cache_hit=cache_hit,
        provider="openai",
        model="gpt-test",
        prompt_version="v1",
        builder_version=1,
        schema_version="ai.test.v3",
        feature=feature,
    )


def _telemetry(*, cache_hit: bool = False, feature: AIFeature = AIFeature.FINDING) -> GenerationTelemetry:
    return GenerationTelemetry(
        generation_id=uuid4(),
        feature=feature,
        provider="openai",
        model="gpt-test",
        prompt_version="v1",
        schema_version="ai.test.v3",
        builder_version=1,
        cache_hit=cache_hit,
        latency_ms=12,
        tokens_in=10,
        tokens_out=20,
        status="cached" if cache_hit else "success",
        retry_count=0,
        created_at=datetime.now(UTC),
    )


def _wrap(result: Any, *, feature: AIFeature, cache_hit: bool = False) -> AIResponse[Any]:
    gid = uuid4()
    return AIResponse(
        result=result,
        generation_id=gid,
        quality=_quality(cache_hit=cache_hit, feature=feature),
        provider_metadata=_meta(cached=cache_hit, feature=feature).model_copy(
            update={"generation_id": gid}
        ),
        diagnostics=None,
        telemetry=_telemetry(cache_hit=cache_hit, feature=feature).model_copy(
            update={"generation_id": gid}
        ),
        session_id=uuid4(),
        generated_at=datetime.now(UTC),
    )


class StubAIService:
    """Mock AIService — no network, controllable failures / cache hits."""

    def __init__(self) -> None:
        self.calls: list[tuple[str, Any]] = []
        self.fail_with: BaseException | None = None
        self.cache_hit = False

    async def explain_finding(self, context: Any, **_: Any) -> AIResponse[FindingExplanation]:
        self.calls.append(("explain_finding", context))
        if self.fail_with:
            raise self.fail_with
        return _wrap(
            FindingExplanation(
                finding_id=context.finding.finding_id,
                title=context.finding.title,
                explanation="Missing viewport hurts mobile SEO.",
                why_it_matters="Mobile ranking and usability.",
                suggested_fix_summary="Add a viewport meta tag.",
                severity=context.finding.severity,
                category=context.finding.category,
            ),
            feature=AIFeature.FINDING,
            cache_hit=self.cache_hit,
        )

    async def explain_recommendation(
        self, context: Any, **_: Any
    ) -> AIResponse[RecommendationExplanation]:
        self.calls.append(("explain_recommendation", context))
        if self.fail_with:
            raise self.fail_with
        rec = context.recommendation
        return _wrap(
            RecommendationExplanation(
                recommendation_id=rec.recommendation_id,
                rule_id=rec.rule_id,
                title=rec.title,
                summary="Add a viewport meta tag.",
                why_it_matters="Improves mobile SEO.",
                how_to_fix="Insert meta viewport in head.",
                expected_benefit="Better mobile indexing.",
                technical_details=rec.technical_reason or "",
                estimated_effort=rec.effort,
            ),
            feature=AIFeature.RECOMMENDATION,
            cache_hit=self.cache_hit,
        )

    async def generate_executive_summary(
        self, context: Any, **_: Any
    ) -> AIResponse[ExecutiveSummary]:
        self.calls.append(("generate_executive_summary", context))
        if self.fail_with:
            raise self.fail_with
        return _wrap(
            ExecutiveSummary(
                headline="Solid foundation with a few high-impact gaps",
                summary="Overall score is strong; fix viewport next.",
                key_risks=["Missing viewport"],
                priority_actions=["Add viewport meta"],
                positive_observations=["Strong security baseline"],
                overall_score=context.health_score,
            ),
            feature=AIFeature.EXECUTIVE_SUMMARY,
            cache_hit=self.cache_hit,
        )

    async def generate_business_summary(
        self, context: Any, **_: Any
    ) -> AIResponse[BusinessSummary]:
        self.calls.append(("generate_business_summary", context))
        if self.fail_with:
            raise self.fail_with
        return _wrap(
            BusinessSummary(
                headline="Business impact is contained",
                summary="One mobile SEO gap affects discovery.",
                key_risks=["Mobile discovery"],
                priority_actions=["Ship viewport fix"],
                positive_observations=["Clear value proposition"],
                customer_impact="Some mobile visitors may bounce.",
                business_opportunities=["Improve organic CTR"],
                overall_score=context.health_score,
            ),
            feature=AIFeature.BUSINESS_SUMMARY,
            cache_hit=self.cache_hit,
        )

    async def generate_quick_win(
        self, context: Any, **_: Any
    ) -> AIResponse[QuickWinExplanation]:
        self.calls.append(("generate_quick_win", context))
        if self.fail_with:
            raise self.fail_with
        qw = context.quick_win
        return _wrap(
            QuickWinExplanation(
                headline="Fast mobile SEO win",
                summary="Viewport is a low-effort high-impact fix.",
                why_it_matters="Unblocks mobile usability signals.",
                expected_benefit="Better mobile rankings.",
                implementation_tip="Add one meta tag in head.",
                recommendation_id=qw.recommendation_id,
                rule_id=qw.rule_id,
                title=qw.title,
                priority=qw.priority,
                category=qw.category,
                estimated_effort=qw.effort,
                estimated_impact=qw.impact,
            ),
            feature=AIFeature.QUICK_WIN,
            cache_hit=self.cache_hit,
        )


@pytest_asyncio.fixture()
async def stub_ai() -> StubAIService:
    return StubAIService()


@pytest_asyncio.fixture()
async def api_client(
    db_engine: AsyncEngine,
    settings: Settings,
    stub_ai: StubAIService,
) -> AsyncIterator[AsyncClient]:
    factory = async_sessionmaker(db_engine, class_=AsyncSession, expire_on_commit=False)

    async def override_db() -> AsyncIterator[AsyncSession]:
        async with factory() as session:
            try:
                yield session
                await session.commit()
            except Exception:
                await session.rollback()
                raise

    app = create_app(settings)
    await app.state.engine.dispose()
    app.state.engine = db_engine
    app.state.session_factory = factory
    app.dependency_overrides[get_db_session] = override_db
    app.dependency_overrides[get_ai_service] = lambda: stub_ai

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        yield client

    app.dependency_overrides.clear()
    clear_settings_cache()
    get_ai_service.cache_clear()


async def _seed(
    session: AsyncSession,
    *,
    status: str = AuditStatus.COMPLETE.value,
    is_quick_win: bool = True,
) -> tuple[AuditRun, AuditFinding, RecommendationRow]:
    org = await OrganizationRepository(session).create(
        OrganizationCreate(name="AI API Org", slug=f"ai-api-{uuid4().hex[:8]}")
    )
    project = await ProjectRepository(session).create(
        ProjectCreate(
            organization_id=org.id,
            name="AI API Project",
            slug=f"ai-api-p-{uuid4().hex[:8]}",
        )
    )
    website = await WebsiteRepository(session).create(
        WebsiteCreate(project_id=project.id, url="https://ai-api.example")
    )
    now = datetime.now(UTC)
    audit = AuditRun(
        website_id=website.id,
        organization_id=org.id,
        project_id=project.id,
        requested_url="https://ai-api.example/",
        canonical_url="https://ai-api.example/",
        status=status,
        progress_percent=100 if status.startswith("complete") else 10,
        started_at=now,
        completed_at=now if status.startswith("complete") else None,
        duration_ms=1000 if status.startswith("complete") else None,
        health_score=90 if status.startswith("complete") else None,
        engine_versions={},
        pipeline_metadata={},
    )
    session.add(audit)
    await session.flush()

    finding = AuditFinding(
        audit_run_id=audit.id,
        engine_name="seo",
        finding_id="seo.viewport.missing",
        category="seo",
        severity="high",
        status="fail",
        issue="Missing viewport",
        technical_detail="No viewport meta",
        evidence={},
        confidence=100,
    )
    rec = RecommendationRow(
        audit_run_id=audit.id,
        recommendation_id="rec.seo.add_viewport",
        title="Add viewport",
        recommendation_text="Add viewport meta tag.",
        technical_reason="Missing viewport meta.",
        business_explanation="Improves mobile SEO.",
        category="SEO",
        priority="High",
        estimated_effort="Very Low",
        estimated_impact="High",
        priority_score=70,
        confidence=90,
        is_quick_win=is_quick_win,
        affected_findings=["seo.viewport.missing"],
        related_rules=["seo.viewport"],
        prompt_version="recommendation_rules@test",
        model_used="rules:v1",
        provider="rules",
        version=1,
        is_fallback=False,
    )

    if status.startswith("complete"):
        session.add(
            HealthScore(
                audit_run_id=audit.id,
                overall_score=90,
                seo_score=90,
                accessibility_score=90,
                security_score=90,
                performance_score=90,
                business_score=90,
                grade="A-",
                confidence=95,
                category_scores={
                    "seo": 90,
                    "accessibility": 90,
                    "security": 90,
                    "performance": 90,
                    "business": 90,
                },
                breakdown={},
                penalties={"items": []},
                configuration_version="scoring_config@test",
            )
        )
        session.add(finding)
        session.add(rec)

    await session.commit()
    await session.refresh(audit)
    if status.startswith("complete"):
        await session.refresh(finding)
        await session.refresh(rec)
    return audit, finding, rec


@pytest.mark.asyncio
async def test_executive_summary_endpoint(
    api_client: AsyncClient, db_session: AsyncSession, stub_ai: StubAIService
) -> None:
    audit, _, _ = await _seed(db_session)
    resp = await api_client.get(f"/api/v1/audits/{audit.id}/ai/executive-summary")
    assert resp.status_code == 200
    body = resp.json()
    assert body["generation_id"]
    assert body["result"]["headline"]
    assert body["provider_metadata"]["provider"] == "openai"
    assert body["quality"]["grounded"] is True
    assert body["telemetry"]["feature"] == AIFeature.EXECUTIVE_SUMMARY.value
    assert resp.headers["X-Generation-ID"] == body["generation_id"]
    assert resp.headers["X-AI-Provider"] == "openai"
    assert resp.headers["X-AI-Model"] == "gpt-test"
    assert resp.headers["X-AI-Cached"] == "false"
    assert resp.headers["X-AI-Feature"] == AIFeature.EXECUTIVE_SUMMARY.value
    assert stub_ai.calls[0][0] == "generate_executive_summary"


@pytest.mark.asyncio
async def test_business_summary_endpoint(
    api_client: AsyncClient, db_session: AsyncSession
) -> None:
    audit, _, _ = await _seed(db_session)
    resp = await api_client.get(f"/api/v1/audits/{audit.id}/ai/business-summary")
    assert resp.status_code == 200
    assert resp.json()["result"]["customer_impact"]


@pytest.mark.asyncio
async def test_finding_explanation_endpoint(
    api_client: AsyncClient, db_session: AsyncSession, stub_ai: StubAIService
) -> None:
    _, finding, _ = await _seed(db_session)
    resp = await api_client.get(f"/api/v1/findings/{finding.id}/ai/explanation")
    assert resp.status_code == 200
    body = resp.json()
    assert body["result"]["finding_id"] == "seo.viewport.missing"
    assert stub_ai.calls[0][0] == "explain_finding"


@pytest.mark.asyncio
async def test_recommendation_explanation_endpoint(
    api_client: AsyncClient, db_session: AsyncSession
) -> None:
    _, _, rec = await _seed(db_session)
    resp = await api_client.get(f"/api/v1/recommendations/{rec.id}/ai/explanation")
    assert resp.status_code == 200
    assert resp.json()["result"]["recommendation_id"] == "rec.seo.add_viewport"


@pytest.mark.asyncio
async def test_quick_win_endpoint(
    api_client: AsyncClient, db_session: AsyncSession
) -> None:
    _, _, rec = await _seed(db_session, is_quick_win=True)
    resp = await api_client.get(f"/api/v1/recommendations/{rec.id}/ai/quick-win")
    assert resp.status_code == 200
    assert resp.json()["result"]["recommendation_id"] == "rec.seo.add_viewport"


@pytest.mark.asyncio
async def test_quick_win_not_available(
    api_client: AsyncClient, db_session: AsyncSession
) -> None:
    _, _, rec = await _seed(db_session, is_quick_win=False)
    resp = await api_client.get(f"/api/v1/recommendations/{rec.id}/ai/quick-win")
    assert resp.status_code == 409
    assert resp.json()["error"]["code"] == "AI_FEATURE_UNAVAILABLE"


@pytest.mark.asyncio
async def test_audit_not_found(api_client: AsyncClient) -> None:
    resp = await api_client.get(f"/api/v1/audits/{uuid4()}/ai/executive-summary")
    assert resp.status_code == 404
    assert resp.json()["error"]["code"] == "AUDIT_NOT_FOUND"


@pytest.mark.asyncio
async def test_audit_not_completed(
    api_client: AsyncClient, db_session: AsyncSession
) -> None:
    audit, _, _ = await _seed(db_session, status=AuditStatus.ANALYZING.value)
    resp = await api_client.get(f"/api/v1/audits/{audit.id}/ai/executive-summary")
    assert resp.status_code == 409
    assert resp.json()["error"]["code"] == "REPORT_NOT_READY"


@pytest.mark.asyncio
async def test_finding_not_found(api_client: AsyncClient) -> None:
    resp = await api_client.get(f"/api/v1/findings/{uuid4()}/ai/explanation")
    assert resp.status_code == 404
    assert resp.json()["error"]["code"] == "FINDING_NOT_FOUND"


@pytest.mark.asyncio
async def test_recommendation_not_found(api_client: AsyncClient) -> None:
    resp = await api_client.get(f"/api/v1/recommendations/{uuid4()}/ai/explanation")
    assert resp.status_code == 404
    assert resp.json()["error"]["code"] == "RECOMMENDATION_NOT_FOUND"


@pytest.mark.asyncio
async def test_grounding_failure_maps_to_422(
    api_client: AsyncClient, db_session: AsyncSession, stub_ai: StubAIService
) -> None:
    audit, _, _ = await _seed(db_session)
    stub_ai.fail_with = InvalidAIResponse("Grounding failed: score mismatch")
    resp = await api_client.get(f"/api/v1/audits/{audit.id}/ai/executive-summary")
    assert resp.status_code == 422
    assert resp.json()["error"]["code"] == "INVALID_AI_RESPONSE"


@pytest.mark.asyncio
async def test_provider_failure_maps_to_503(
    api_client: AsyncClient, db_session: AsyncSession, stub_ai: StubAIService
) -> None:
    audit, _, _ = await _seed(db_session)
    stub_ai.fail_with = AIProviderError("timeout talking to OpenAI")
    resp = await api_client.get(f"/api/v1/audits/{audit.id}/ai/business-summary")
    assert resp.status_code == 503
    assert resp.json()["error"]["code"] == "UPSTREAM_UNAVAILABLE"


@pytest.mark.asyncio
async def test_configuration_missing_maps_to_503(
    api_client: AsyncClient, db_session: AsyncSession, stub_ai: StubAIService
) -> None:
    _, finding, _ = await _seed(db_session)
    stub_ai.fail_with = AIConfigurationError("OPENAI_API_KEY missing")
    resp = await api_client.get(f"/api/v1/findings/{finding.id}/ai/explanation")
    assert resp.status_code == 503
    assert resp.json()["error"]["code"] == "NOT_READY"


@pytest.mark.asyncio
async def test_cache_hit_propagated(
    api_client: AsyncClient, db_session: AsyncSession, stub_ai: StubAIService
) -> None:
    audit, _, _ = await _seed(db_session)
    stub_ai.cache_hit = True
    resp = await api_client.get(f"/api/v1/audits/{audit.id}/ai/executive-summary")
    assert resp.status_code == 200
    body = resp.json()
    assert body["quality"]["cache_hit"] is True
    assert body["provider_metadata"]["cached"] is True
    assert body["telemetry"]["cache_hit"] is True
    assert resp.headers["X-AI-Cached"] == "true"


@pytest.mark.asyncio
async def test_dependency_injection_uses_override(
    api_client: AsyncClient, db_session: AsyncSession, stub_ai: StubAIService
) -> None:
    audit, _, _ = await _seed(db_session)
    await api_client.get(f"/api/v1/audits/{audit.id}/ai/executive-summary")
    assert len(stub_ai.calls) == 1
    assert not isinstance(stub_ai, AIService)


@pytest.mark.asyncio
async def test_seeded_row_ids_are_uuid_primary_keys(
    db_session: AsyncSession,
) -> None:
    _, finding, rec = await _seed(db_session)
    assert isinstance(finding.id, UUID)
    assert isinstance(rec.id, UUID)
    loaded = (
        await db_session.execute(select(AuditFinding).where(AuditFinding.id == finding.id))
    ).scalar_one()
    assert loaded.finding_id == "seo.viewport.missing"

"""Sprint 23.1 — AI API refinement (headers, OpenAPI, split routers, helper)."""

from __future__ import annotations

from datetime import UTC, datetime
from uuid import uuid4

from fastapi import FastAPI

from app.ai.features import AIFeature
from app.ai.response import AIQualityMetadata, AIResponse, ProviderResponseMetadata
from app.ai.schemas import FindingExplanation
from app.api.v1.ai import (
    audits_ai_router,
    findings_ai_router,
    recommendations_ai_router,
)
from app.api.v1.ai.response import (
    HEADER_AI_CACHED,
    HEADER_AI_FEATURE,
    HEADER_AI_MODEL,
    HEADER_AI_PROVIDER,
    HEADER_GENERATION_ID,
    ai_json_response,
    ai_response_headers,
)
from app.api.v1.router import router as v1_router
from app.main import create_app


def _sample_response(*, cached: bool = False) -> AIResponse[FindingExplanation]:
    gid = uuid4()
    return AIResponse(
        result=FindingExplanation(
            finding_id="seo.viewport.missing",
            title="Missing viewport",
            explanation="e",
            why_it_matters="w",
            suggested_fix_summary="f",
            severity="high",
            category="seo",
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
            schema_version="ai.finding_explanation.v3",
            feature=AIFeature.FINDING,
        ),
        provider_metadata=ProviderResponseMetadata(
            generation_id=gid,
            feature=AIFeature.FINDING,
            provider="openai",
            model="gpt-test",
            cached=cached,
            retry_count=0,
        ),
        session_id=uuid4(),
        generated_at=datetime.now(UTC),
    )


def test_ai_response_headers_from_existing_metadata() -> None:
    response = _sample_response(cached=True)
    headers = ai_response_headers(response)
    assert headers[HEADER_GENERATION_ID] == str(response.generation_id)
    assert headers[HEADER_AI_PROVIDER] == "openai"
    assert headers[HEADER_AI_MODEL] == "gpt-test"
    assert headers[HEADER_AI_CACHED] == "true"
    assert headers[HEADER_AI_FEATURE] == AIFeature.FINDING.value


def test_ai_json_response_preserves_body_and_adds_headers() -> None:
    response = _sample_response()
    http = ai_json_response(response)
    assert http.status_code == 200
    body = response.model_dump(mode="json")
    assert http.body  # serialized
    # Re-parse via content equality with model_dump
    import json

    assert json.loads(http.body) == body
    assert http.headers[HEADER_GENERATION_ID] == str(response.generation_id)
    assert http.headers[HEADER_AI_CACHED] == "false"


def test_split_routers_exported() -> None:
    assert audits_ai_router.prefix == "/audits"
    assert findings_ai_router.prefix == "/findings"
    assert recommendations_ai_router.prefix == "/recommendations"
    assert audits_ai_router.tags == ["AI"]
    assert findings_ai_router.tags == ["AI"]
    assert recommendations_ai_router.tags == ["AI"]


def test_v1_router_registers_ai_routes() -> None:
    paths = {
        getattr(route, "path", None)
        for mount in (audits_ai_router, findings_ai_router, recommendations_ai_router)
        for route in mount.routes
    }
    assert "/audits/{audit_id}/ai/executive-summary" in paths
    assert "/audits/{audit_id}/ai/business-summary" in paths
    assert "/findings/{finding_id}/ai/explanation" in paths
    assert "/recommendations/{recommendation_id}/ai/explanation" in paths
    assert "/recommendations/{recommendation_id}/ai/quick-win" in paths
    # Feature routers are included on the v1 aggregate (5 top-level mounts).
    assert len(v1_router.routes) >= 5


def test_openapi_ai_tags_and_operation_ids() -> None:
    app: FastAPI = create_app()
    schema = app.openapi()
    paths = schema["paths"]

    expected = {
        "/api/v1/audits/{audit_id}/ai/executive-summary": "getAuditAiExecutiveSummary",
        "/api/v1/audits/{audit_id}/ai/business-summary": "getAuditAiBusinessSummary",
        "/api/v1/findings/{finding_id}/ai/explanation": "getFindingAiExplanation",
        "/api/v1/recommendations/{recommendation_id}/ai/explanation": (
            "getRecommendationAiExplanation"
        ),
        "/api/v1/recommendations/{recommendation_id}/ai/quick-win": (
            "getRecommendationAiQuickWin"
        ),
    }
    for path, op_id in expected.items():
        assert path in paths, path
        op = paths[path]["get"]
        assert op["operationId"] == op_id
        assert "AI" in op["tags"]
        assert op.get("summary")
        assert op.get("description")

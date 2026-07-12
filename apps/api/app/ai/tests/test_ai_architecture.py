"""Tests for AI foundation architecture (builders, context, response, telemetry)."""

from __future__ import annotations

import ast
import os
from datetime import UTC, datetime
from pathlib import Path
from uuid import uuid4

import pytest

from app.ai.builders import (
    BusinessSummaryBuilder,
    ExecutiveSummaryBuilder,
    FindingExplanationBuilder,
    QuickWinBuilder,
    RecommendationExplanationBuilder,
)
from app.ai.cache import AICache, NullAICache, build_cache_key, hash_input_payload
from app.ai.config import AISettings, clear_ai_settings_cache
from app.ai.constants import (
    SCHEMA_VERSION_BUSINESS_SUMMARY,
    SCHEMA_VERSION_EXECUTIVE_SUMMARY,
    SCHEMA_VERSION_FINDING_EXPLANATION,
    SCHEMA_VERSION_QUICK_WIN,
)
from app.ai.context import (
    AIContext,
    BusinessSummaryInputs,
    ExecutiveSummaryInputs,
    FindingContext,
    QuickWinContext,
    RecommendationContext,
    WebsiteContext,
)
from app.ai.exceptions import (
    AIConfigurationError,
    PromptValidationError,
    ProviderNotFound,
)
from app.ai.factory import ProviderFactory
from app.ai.openai_settings import clear_openai_settings_cache
from app.ai.prompt_repository import PromptRepository
from app.ai.registry import ProviderRegistry, reset_provider_registry
from app.ai.response import AIResponse, ProviderResponseMetadata
from app.ai.schemas import FindingExplanation
from app.ai.service import AIService
from app.ai.telemetry import GenerationTelemetry


@pytest.fixture(autouse=True)
def _reset_ai_singletons(monkeypatch: pytest.MonkeyPatch) -> None:
    clear_ai_settings_cache()
    clear_openai_settings_cache()
    reset_provider_registry()
    for key in list(os.environ):
        if key.startswith("AI_") or key.startswith("OPENAI_"):
            monkeypatch.delenv(key, raising=False)
    clear_ai_settings_cache()
    clear_openai_settings_cache()
    yield
    clear_ai_settings_cache()
    clear_openai_settings_cache()
    reset_provider_registry()


def _website() -> WebsiteContext:
    return WebsiteContext(
        url="https://example.com",
        canonical_url="https://example.com/",
        host="example.com",
        title="Example",
        is_https=True,
    )


def _finding() -> FindingContext:
    return FindingContext(
        finding_id="seo.title.missing",
        title="Missing title",
        description="No title tag",
        severity="high",
        category="seo",
        status="fail",
        business_impact="Lower CTR",
        confidence=95,
    )


def _recommendation() -> RecommendationContext:
    return RecommendationContext(
        recommendation_id="rec.seo.add_document_title",
        rule_id="seo.title.missing",
        title="Add a descriptive document title",
        description="Set a unique title.",
        priority="High",
        category="SEO",
        effort="Very Low",
        impact="High",
        business_reason="Improves CTR",
        related_rules=("seo.title.missing",),
        related_findings=(
            FindingContext(
                finding_id="seo.title.missing",
                title="Missing title",
                severity="high",
                category="seo",
            ),
        ),
        is_quick_win=True,
    )


def _finding_context(**overrides: object) -> AIContext:
    base: dict[str, object] = {
        "audit_id": uuid4(),
        "report_hash": "abc123",
        "schema_version": SCHEMA_VERSION_FINDING_EXPLANATION,
        "locale": "en",
        "website": _website(),
        "health_score": 81,
        "category": "seo",
        "finding": _finding(),
    }
    base.update(overrides)
    return AIContext.model_validate(base)


class TestAIContext:
    def test_immutable_and_prompt_safe(self) -> None:
        ctx = _finding_context()
        assert ctx.finding is not None
        assert ctx.finding.finding_id == "seo.title.missing"
        with pytest.raises(Exception):
            ctx.health_score = 10  # type: ignore[misc]

    def test_rejects_extra_fields(self) -> None:
        with pytest.raises(Exception):
            AIContext.model_validate(
                {
                    "schema_version": "ai.finding_explanation.v1",
                    "orm_row": {"id": 1},
                }
            )


class TestAIResponse:
    def test_generic_envelope(self) -> None:
        result = FindingExplanation(
            finding_id="seo.title.missing",
            title="Missing title",
            explanation="No title.",
            why_it_matters="CTR",
            suggested_fix_summary="Add title",
            severity="high",
            category="seo",
        )
        response = AIResponse[FindingExplanation](
            result=result,
            provider_metadata=ProviderResponseMetadata(
                provider="openai",
                model="gpt-5.5",
                cached=False,
                latency_ms=12,
                tokens_in=100,
                tokens_out=40,
                cost_usd=0.001,
            ),
            generated_at=datetime.now(UTC),
        )
        assert response.result.finding_id == "seo.title.missing"
        assert response.provider_metadata.provider == "openai"
        assert response.metadata.cached is False  # alias


class TestTelemetry:
    def test_telemetry_model(self) -> None:
        tel = GenerationTelemetry(
            provider="openai",
            model="gpt-4o-mini",
            prompt_version="finding_explanation@v1",
            schema_version=SCHEMA_VERSION_FINDING_EXPLANATION,
            cache_hit=False,
            latency_ms=10,
            tokens_in=1,
            tokens_out=2,
            cost_usd=0.0,
            status="not_implemented",
            error=None,
            request_id="req_1",
            created_at=datetime.now(UTC),
        )
        assert tel.status == "not_implemented"
        assert tel.cache_hit is False


class TestCache:
    def test_build_cache_key_deterministic(self) -> None:
        a = build_cache_key(
            provider="OpenAI",
            model="gpt-4o-mini",
            schema_version="ai.finding_explanation.v1",
            builder_version=1,
            prompt_version="finding_explanation@v1",
            report_hash="abc",
            input_hash="def",
        )
        b = build_cache_key(
            provider="openai",
            model="gpt-4o-mini",
            schema_version="ai.finding_explanation.v1",
            builder_version=1,
            prompt_version="finding_explanation@v1",
            report_hash="abc",
            input_hash="def",
        )
        assert a == b
        assert len(a) == 64

    def test_input_hash_stable(self) -> None:
        assert hash_input_payload({"b": 1, "a": 2}) == hash_input_payload({"a": 2, "b": 1})

    def test_schema_version_changes_key(self) -> None:
        a = build_cache_key(
            provider="openai",
            model="gpt-4o-mini",
            schema_version="ai.finding_explanation.v1",
            builder_version=1,
            prompt_version="finding_explanation@v1",
            report_hash="r1",
            input_hash="i1",
        )
        b = build_cache_key(
            provider="openai",
            model="gpt-4o-mini",
            schema_version="ai.finding_explanation.v2",
            builder_version=1,
            prompt_version="finding_explanation@v1",
            report_hash="r1",
            input_hash="i1",
        )
        assert a != b

    def test_deterministic_kwargs(self) -> None:
        kwargs = {
            "provider": "OpenAI",
            "model": "gpt-4o-mini",
            "schema_version": "ai.finding_explanation.v1",
            "builder_version": 1,
            "prompt_version": "v1",
            "report_hash": "r",
            "input_hash": "i",
        }
        assert build_cache_key(**kwargs) == build_cache_key(
            provider="openai",
            model="gpt-4o-mini",
            schema_version="ai.finding_explanation.v1",
            builder_version=1,
            prompt_version="v1",
            report_hash="r",
            input_hash="i",
        )


class TestPromptBuilders:
    def test_finding_builder(self) -> None:
        built = FindingExplanationBuilder(PromptRepository()).build(_finding_context())
        assert built.prompt_id == "finding_explanation"
        assert built.prompt_version == "v2"
        assert built.schema_version == SCHEMA_VERSION_FINDING_EXPLANATION
        assert "seo.title.missing" in built.prompt
        assert built.input_hash

    def test_recommendation_builder(self) -> None:
        ctx = _finding_context(
            schema_version="ai.recommendation.v1",
            recommendation=_recommendation(),
        )
        built = RecommendationExplanationBuilder(PromptRepository()).build(ctx)
        assert built.prompt_id == "recommendation"
        assert "rec.seo.add_document_title" in built.prompt

    def test_executive_summary_builder(self) -> None:
        ctx = AIContext(
            schema_version=SCHEMA_VERSION_EXECUTIVE_SUMMARY,
            report_hash="rh",
            website=_website(),
            health_score=81,
            executive_summary_inputs=ExecutiveSummaryInputs(
                summary="Analysis complete.",
                overall_score=81,
                grade="B-",
                critical_issues=("Non-HTTPS URL",),
                statistics={"findings": 4},
            ),
        )
        built = ExecutiveSummaryBuilder(PromptRepository()).build(ctx)
        assert built.prompt_id == "executive_summary"
        assert "Analysis complete." in built.prompt

    def test_business_summary_builder(self) -> None:
        ctx = AIContext(
            schema_version=SCHEMA_VERSION_BUSINESS_SUMMARY,
            website=_website(),
            health_score=81,
            business_summary_inputs=BusinessSummaryInputs(
                summary="Trust gaps",
                overall_score=81,
                grade="B-",
                business_impacts=("Lower CTR",),
                recommendation_titles=("Add title",),
                recommendations=("Add title",),
            ),
        )
        built = BusinessSummaryBuilder(PromptRepository()).build(ctx)
        assert built.prompt_id == "business_summary"
        assert built.schema_version == SCHEMA_VERSION_BUSINESS_SUMMARY
        assert "Trust gaps" in built.prompt

    def test_quick_win_builder(self) -> None:
        rec = _recommendation()
        ctx = AIContext(
            schema_version=SCHEMA_VERSION_QUICK_WIN,
            website=_website(),
            health_score=81,
            category=rec.category,
            quick_win=QuickWinContext(
                recommendation_id=rec.recommendation_id,
                rule_id=rec.rule_id,
                title=rec.title,
                description=rec.description,
                priority=rec.priority,
                category=rec.category,
                effort=rec.effort,
                impact=rec.impact,
                business_reason=rec.business_reason,
                is_quick_win=True,
            ),
        )
        built = QuickWinBuilder(PromptRepository()).build(ctx)
        assert built.prompt_id == "quick_win"
        assert "Very Low" in built.prompt

    def test_builder_requires_context_fields(self) -> None:
        ctx = AIContext(schema_version=SCHEMA_VERSION_FINDING_EXPLANATION)
        with pytest.raises(PromptValidationError):
            FindingExplanationBuilder(PromptRepository()).build(ctx)

    def test_prompt_version_exposed(self) -> None:
        builder = FindingExplanationBuilder(PromptRepository())
        assert builder.prompt_version == "v2"


class TestPromptIsolation:
    def test_builders_have_no_sqlalchemy_imports(self) -> None:
        builders_dir = Path(__file__).resolve().parents[1] / "builders"
        for path in builders_dir.glob("*.py"):
            tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
            for node in ast.walk(tree):
                if isinstance(node, ast.Import):
                    for alias in node.names:
                        assert "sqlalchemy" not in alias.name
                if isinstance(node, ast.ImportFrom) and node.module:
                    assert not node.module.startswith("sqlalchemy")
                    assert not node.module.startswith("app.models")
                    assert not node.module.startswith("app.repositories")

    def test_providers_do_not_import_grounding_or_engines(self) -> None:
        providers_dir = Path(__file__).resolve().parents[1] / "providers"
        forbidden = (
            "app.ai.grounding",
            "app.engines",
            "app.pipeline",
            "app.services.report",
            "app.models",
            "app.repositories",
        )
        for path in providers_dir.glob("*.py"):
            tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
            for node in ast.walk(tree):
                if isinstance(node, ast.ImportFrom) and node.module:
                    assert not any(node.module.startswith(p) for p in forbidden), path
                if isinstance(node, ast.Import):
                    for alias in node.names:
                        assert not any(alias.name.startswith(p) for p in forbidden), path

    def test_grounding_has_no_openai_or_engine_imports(self) -> None:
        grounding_dir = Path(__file__).resolve().parents[1] / "grounding"
        forbidden = (
            "openai",
            "app.engines",
            "app.pipeline",
            "app.services.report",
            "app.ai.providers",
        )
        for path in grounding_dir.glob("*.py"):
            tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
            for node in ast.walk(tree):
                if isinstance(node, ast.ImportFrom) and node.module:
                    assert not any(
                        node.module == p or node.module.startswith(p + ".")
                        for p in forbidden
                    ), path
                if isinstance(node, ast.Import):
                    for alias in node.names:
                        assert not any(
                            alias.name == p or alias.name.startswith(p + ".")
                            for p in forbidden
                        ), path


class TestServiceOrchestration:
    def _service(self) -> AIService:
        settings = AISettings()
        factory = ProviderFactory(settings)
        registry = ProviderRegistry()
        factory.populate_registry(registry)
        return AIService(
            settings=settings,
            registry=registry,
            factory=factory,
            prompts=PromptRepository(),
            cache=NullAICache(),
        )

    def test_factory_and_registry_still_work(self) -> None:
        factory = ProviderFactory(AISettings())
        registry = ProviderRegistry()
        factory.populate_registry(registry)
        assert registry.get().name() == "gemini"
        assert factory.create("gemini").name() == "gemini"
        with pytest.raises(ProviderNotFound):
            factory.create("nope")

    def test_service_builds_via_builders_not_manual_vars(self) -> None:
        service = self._service()
        ctx = _finding_context()
        built = service.build_finding_prompt(ctx)
        assert built.schema_version == SCHEMA_VERSION_FINDING_EXPLANATION
        assert built.builder_version == 1
        key = service.build_cache_key_for(built, context=ctx)
        request = service.build_generation_request(
            ctx, built, expected_output_type=FindingExplanation
        )
        assert request.cache_key == key
        assert request.schema_version == built.schema_version
        assert request.builder_version == built.builder_version
        assert request.expected_output_type is FindingExplanation
        assert "seo.title.missing" in request.rendered_text

    @pytest.mark.asyncio
    async def test_generation_returns_ai_response_type_contract(self) -> None:
        service = self._service()
        ctx = _finding_context(recommendation=_recommendation())
        # FindingExplanation is wired via OpenAI (Sprint 18); without a key → config error.
        with pytest.raises(AIConfigurationError):
            await service.explain_finding(ctx)
        # RecommendationExplanation is wired; without a key → config error.
        with pytest.raises(AIConfigurationError):
            await service.explain_recommendation(ctx)
        qw_ctx = AIContext(
            schema_version=SCHEMA_VERSION_QUICK_WIN,
            website=_website(),
            quick_win=QuickWinContext(
                recommendation_id="rec.seo.add_document_title",
                rule_id="seo.title.missing",
                title="Add title",
                description="Add title",
                priority="High",
                category="SEO",
                effort="Very Low",
                impact="High",
            ),
        )
        with pytest.raises(AIConfigurationError):
            await service.generate_quick_win(qw_ctx)

        exec_ctx = AIContext(
            schema_version=SCHEMA_VERSION_EXECUTIVE_SUMMARY,
            website=_website(),
            executive_summary_inputs=ExecutiveSummaryInputs(summary="S"),
        )
        with pytest.raises(AIConfigurationError):
            await service.generate_executive_summary(exec_ctx)

        biz_ctx = AIContext(
            schema_version=SCHEMA_VERSION_BUSINESS_SUMMARY,
            website=_website(),
            business_summary_inputs=BusinessSummaryInputs(
                summary="B",
                overall_score=80,
                grade="B",
            ),
        )
        with pytest.raises(AIConfigurationError):
            await service.generate_business_summary(biz_ctx)

    def test_provider_resolution_unchanged(self) -> None:
        service = self._service()
        assert service.resolve_provider().name() == "gemini"
        from app.ai.providers.gemini import GeminiProvider

        assert isinstance(service.resolve_provider("gemini"), GeminiProvider)


class TestCacheInterface:
    @pytest.mark.asyncio
    async def test_null_cache(self) -> None:
        cache: AICache = NullAICache()
        await cache.set("k", "v")
        assert await cache.get("k") is None

"""Architecture polish tests — capabilities, versioning, readiness."""

from __future__ import annotations

import os
from datetime import UTC, datetime
from uuid import uuid4

import pytest

from app.ai.builders import FindingExplanationBuilder, QuickWinBuilder
from app.ai.cache import build_cache_key
from app.ai.config import AISettings, clear_ai_settings_cache
from app.ai.constants import SCHEMA_VERSION_FINDING_EXPLANATION
from app.ai.context import (
    AIContext,
    ExecutiveSummaryInputs,
    FindingContext,
    RecommendationContext,
    WebsiteContext,
)
from app.ai.exceptions import (
    AIConfigurationError,
    BuilderNotFound,
    CapabilityNotSupported,
    ServiceNotReady,
)
from app.ai.factory import ProviderFactory
from app.ai.generation import GenerationOptions, GenerationRequest
from app.ai.openai_settings import clear_openai_settings_cache
from app.ai.prompt_repository import PromptRepository
from app.ai.provider_capabilities import ProviderCapabilities
from app.ai.providers import OllamaProvider, OpenAIProvider
from app.ai.registry import ProviderRegistry, reset_provider_registry
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


def _ctx() -> AIContext:
    return AIContext(
        audit_id=uuid4(),
        report_hash="rh1",
        schema_version=SCHEMA_VERSION_FINDING_EXPLANATION,
        website=WebsiteContext(url="https://example.com"),
        health_score=80,
        finding=FindingContext(
            finding_id="seo.title.missing",
            title="Missing title",
            severity="high",
            category="seo",
        ),
        recommendation=RecommendationContext(
            recommendation_id="rec.seo.add_document_title",
            rule_id="seo.title.missing",
            title="Add title",
            description="Add it",
            priority="High",
            category="SEO",
            effort="Very Low",
            impact="High",
            related_rules=("seo.title.missing",),
        ),
    )


def _service() -> AIService:
    settings = AISettings()
    factory = ProviderFactory(settings)
    registry = ProviderRegistry()
    factory.populate_registry(registry)
    return AIService(
        settings=settings,
        registry=registry,
        factory=factory,
        prompts=PromptRepository(),
    )


class TestProviderCapabilities:
    def test_capabilities_immutable(self) -> None:
        caps = ProviderCapabilities(
            provider_name="openai",
            supports_json=True,
            supports_streaming=True,
            max_context_tokens=128000,
        )
        assert caps.supports_json is True
        with pytest.raises(Exception):
            caps.supports_json = False  # type: ignore[misc]

    def test_providers_advertise_capabilities(self) -> None:
        openai = OpenAIProvider()
        assert openai.capabilities.provider_name == "openai"
        assert openai.capabilities.supports_json is True
        assert openai.vendor() == "OpenAI"
        assert openai.default_model() == "gpt-5.5"
        assert openai.api_version() == "v1"

        ollama = OllamaProvider()
        assert ollama.capabilities.supports_function_calling is False
        assert ollama.vendor() == "Ollama"


class TestBuilderVersioning:
    def test_builder_version_on_built_prompt(self) -> None:
        built = FindingExplanationBuilder(PromptRepository()).build(_ctx())
        assert FindingExplanationBuilder.BUILDER_VERSION == 1
        assert built.builder_version == 1
        assert built.prompt_version == "v2"
        assert built.diagnostics.template_name == "finding_explanation"
        assert built.diagnostics.template_path is not None
        assert built.estimated_tokens > 0
        assert built.variables_hash == built.input_hash
        assert built.diagnostics.variable_count > 0

    def test_prompt_and_builder_versions_are_independent(self) -> None:
        builder = QuickWinBuilder(PromptRepository())
        assert builder.prompt_version == "v1"
        assert builder.builder_version == 1


class TestAIContextImmutability:
    def test_frozen_and_nested_frozen(self) -> None:
        ctx = _ctx()
        with pytest.raises(Exception):
            ctx.health_score = 1  # type: ignore[misc]
        assert ctx.finding is not None
        with pytest.raises(Exception):
            ctx.finding.title = "x"  # type: ignore[misc]

    def test_statistics_mapping_is_immutable(self) -> None:
        inputs = ExecutiveSummaryInputs(statistics={"findings": 3})
        assert inputs.statistics["findings"] == 3
        with pytest.raises(TypeError):
            inputs.statistics["findings"] = 9  # type: ignore[index]


class TestCacheKeyBuilderVersion:
    def test_builder_version_invalidates_cache(self) -> None:
        base = dict(
            provider="openai",
            model="gpt-4o-mini",
            schema_version="ai.finding_explanation.v1",
            prompt_version="finding_explanation@v1",
            report_hash="r",
            input_hash="i",
        )
        a = build_cache_key(**base, builder_version=1)
        b = build_cache_key(**base, builder_version=2)
        assert a != b


class TestTelemetryFields:
    def test_extended_telemetry(self) -> None:
        tel = GenerationTelemetry(
            provider="openai",
            model="gpt-4o-mini",
            prompt_version="v1",
            schema_version="ai.finding_explanation.v1",
            builder_version=1,
            cache_key="abc",
            report_hash="rh",
            provider_latency_ms=10,
            prompt_build_latency_ms=2,
            validation_latency_ms=1,
            response_parse_latency_ms=3,
            generation_status="not_implemented",
            retry_count=0,
            created_at=datetime.now(UTC),
        )
        assert tel.cache_key == "abc"
        assert tel.builder_version == 1
        assert tel.retry_count == 0


class TestGenerationOptionsAndRequest:
    def test_generation_options_frozen(self) -> None:
        opts = GenerationOptions(json_mode=True, temperature=0.1, seed=42)
        assert opts.json_mode is True
        with pytest.raises(Exception):
            opts.stream = True  # type: ignore[misc]

    def test_generation_request_owns_context_prompt_options(self) -> None:
        service = _service()
        ctx = _ctx()
        built = service.build_finding_prompt(ctx)
        req = service.build_generation_request(
            ctx, built, expected_output_type=FindingExplanation
        )
        assert isinstance(req, GenerationRequest)
        assert req.context.report_hash == "rh1"
        assert req.built_prompt.builder_version == 1
        assert req.expected_output_type is FindingExplanation
        assert req.options.json_mode is True
        assert req.cache_key
        assert req.rendered_text == built.prompt


class TestServiceReadiness:
    def test_unknown_builder(self) -> None:
        service = _service()
        with pytest.raises(BuilderNotFound):
            service.get_builder("nope")
        with pytest.raises(ServiceNotReady):
            service.ensure_ready(builder_key="nope")

    def test_capability_validation_json(self) -> None:
        service = _service()
        provider = OpenAIProvider()
        service.validate_capabilities(provider, GenerationOptions(json_mode=True))

        capped = OllamaProvider()
        # Force a capability rejection by requesting response_schema
        with pytest.raises(CapabilityNotSupported):
            service.validate_capabilities(
                capped,
                GenerationOptions(json_mode=True, response_schema="x"),
            )

    def test_ensure_ready_success(self) -> None:
        service = _service()
        builder, provider, opts = service.ensure_ready(
            builder_key="finding_explanation",
            options=GenerationOptions(json_mode=True),
        )
        assert builder.prompt_id == "finding_explanation"
        assert provider.name() == "gemini"
        assert opts.json_mode is True

    @pytest.mark.asyncio
    async def test_generation_calls_provider_without_key(self) -> None:
        service = _service()
        with pytest.raises(AIConfigurationError):
            await service.explain_finding(_ctx())

"""Final architecture freeze tests — generics, session, diagnostics."""

from __future__ import annotations

import os
from datetime import UTC, datetime
from uuid import uuid4

import pytest

from app.ai.builders import FindingExplanationBuilder
from app.ai.cache import NullAICache
from app.ai.config import AISettings, clear_ai_settings_cache
from app.ai.constants import SCHEMA_VERSION_FINDING_EXPLANATION
from app.ai.context import AIContext, FindingContext, WebsiteContext
from app.ai.diagnostics import PromptDiagnostics
from app.ai.exceptions import AIConfigurationError, ServiceNotReady
from app.ai.factory import ProviderFactory
from app.ai.features import AIFeature
from app.ai.generation import GenerationOptions, GenerationRequest
from app.ai.openai_settings import clear_openai_settings_cache
from app.ai.prompt_repository import PromptRepository
from app.ai.providers import OpenAIProvider
from app.ai.registry import ProviderRegistry, reset_provider_registry
from app.ai.response import AIResponse, ProviderResponseMetadata
from app.ai.schemas import FindingExplanation
from app.ai.service import AIService
from app.ai.session import GenerationSession
from app.ai.telemetry import GenerationTelemetry


@pytest.fixture(autouse=True)
def _reset(monkeypatch: pytest.MonkeyPatch) -> None:
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
        report_hash="rh",
        schema_version=SCHEMA_VERSION_FINDING_EXPLANATION,
        website=WebsiteContext(url="https://example.com"),
        finding=FindingContext(
            finding_id="seo.title.missing",
            title="Missing title",
            severity="high",
            category="seo",
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
        cache=NullAICache(),
    )


class TestPromptDiagnostics:
    def test_builder_populates_diagnostics(self) -> None:
        built = FindingExplanationBuilder(PromptRepository()).build(_ctx())
        diag = built.diagnostics
        assert isinstance(diag, PromptDiagnostics)
        assert diag.template_name == "finding_explanation"
        assert diag.template_path is not None
        assert diag.prompt_version == "v2"
        assert diag.builder_version == 1
        assert diag.estimated_tokens > 0
        assert diag.estimated_prompt_tokens == diag.estimated_tokens
        assert diag.estimated_completion_tokens > 0
        assert diag.context_size > 0
        assert diag.prompt_hash
        assert len(diag.prompt_hash) == 64
        assert built.prompt_hash == diag.prompt_hash
        assert diag.actual_tokens is None
        assert diag.variable_count > 0
        assert diag.variables_hash == built.input_hash
        assert diag.prompt_length == len(built.prompt)
        assert diag.missing_variables == ()


class TestBuiltPromptShape:
    def test_minimal_built_prompt_fields(self) -> None:
        built = FindingExplanationBuilder(PromptRepository()).build(_ctx())
        dumped = built.model_dump()
        assert set(dumped.keys()) == {
            "prompt",
            "diagnostics",
            "schema_version",
            "input_hash",
            "prompt_hash",
        }
        assert built.prompt_id == "finding_explanation"
        assert built.builder_version == 1


class TestGenerationRequestGenerics:
    def test_request_carries_expected_output_type(self) -> None:
        service = _service()
        ctx = _ctx()
        built = service.build_finding_prompt(ctx)
        request = service.build_generation_request(
            ctx,
            built,
            expected_output_type=FindingExplanation,
        )
        assert isinstance(request, GenerationRequest)
        assert request.expected_output_type is FindingExplanation
        assert request.diagnostics.template_name == "finding_explanation"
        assert request.rendered_text == built.prompt


class TestGenerationSessionLifecycle:
    def test_start_finish_duration_and_flags(self) -> None:
        service = _service()
        ctx = _ctx()
        built = service.build_finding_prompt(ctx)
        request = service.build_generation_request(
            ctx, built, expected_output_type=FindingExplanation
        )
        session = service.create_session(request)
        assert isinstance(session, GenerationSession)
        assert session.duration_ms is None

        session.start()
        assert session.started_at is not None
        assert session.telemetry is not None
        assert session.telemetry.status == "not_implemented"

        session.mark_retry()
        assert session.retry_count == 1
        session.mark_cache_hit()
        assert session.cache_hit is True

        result = FindingExplanation(
            finding_id="seo.title.missing",
            title="t",
            explanation="e",
            why_it_matters="w",
            suggested_fix_summary="s",
            severity="high",
            category="seo",
        )
        response = AIResponse[FindingExplanation](
            result=result,
            provider_metadata=ProviderResponseMetadata(
                provider="openai",
                model="gpt-5.5",
            ),
            generated_at=datetime.now(UTC),
            diagnostics=built.diagnostics,
            session_id=session.session_id,
        )
        session.attach_response(response)
        assert session.response is response

        session.finish()
        assert session.finished_at is not None
        assert session.duration_ms is not None
        assert session.duration_ms >= 0

        with pytest.raises(ServiceNotReady):
            session.start()


class TestAIResponseOptionalFields:
    def test_optional_diagnostics_telemetry_session_id(self) -> None:
        result = FindingExplanation(
            finding_id="seo.title.missing",
            title="t",
            explanation="e",
            why_it_matters="w",
            suggested_fix_summary="s",
            severity="high",
            category="seo",
        )
        diag = PromptDiagnostics(
            feature=AIFeature.FINDING,
            template_name="finding_explanation",
            prompt_version="v2",
            builder_version=1,
            prompt_hash="a" * 64,
            estimated_tokens=10,
            estimated_prompt_tokens=10,
            estimated_completion_tokens=128,
            context_size=40,
            variable_count=1,
            variables_hash="h",
            prompt_length=40,
        )
        tel = GenerationTelemetry(
            provider="openai",
            model="gpt-5.5",
            prompt_version="v2",
            schema_version=SCHEMA_VERSION_FINDING_EXPLANATION,
            created_at=datetime.now(UTC),
        )
        response = AIResponse[FindingExplanation](
            result=result,
            provider_metadata=ProviderResponseMetadata(
                provider="openai",
                model="gpt-5.5",
            ),
            generated_at=datetime.now(UTC),
            diagnostics=diag,
            telemetry=tel,
            session_id="sess-1",
        )
        assert response.diagnostics is diag
        assert response.telemetry is tel
        assert response.session_id == "sess-1"

        bare = AIResponse[FindingExplanation](
            result=result,
            provider_metadata=ProviderResponseMetadata(
                provider="openai",
                model="gpt-5.5",
            ),
            generated_at=datetime.now(UTC),
        )
        assert bare.diagnostics is None
        assert bare.telemetry is None
        assert bare.session_id is None


class TestProviderGenericContract:
    @pytest.mark.asyncio
    async def test_generate_accepts_generation_request(self) -> None:
        service = _service()
        ctx = _ctx()
        built = service.build_finding_prompt(ctx)
        request = service.build_generation_request(
            ctx, built, expected_output_type=FindingExplanation
        )
        provider = OpenAIProvider(api_key=None)
        with pytest.raises(AIConfigurationError):
            await provider.generate(request)


class TestServiceSessionOrchestration:
    @pytest.mark.asyncio
    async def test_explain_finding_requires_openai_key_without_mock(self) -> None:
        service = _service()
        with pytest.raises(AIConfigurationError):
            await service.explain_finding(_ctx())
    def test_create_session_explicit(self) -> None:
        service = _service()
        ctx = _ctx()
        built = service.build_finding_prompt(ctx)
        request = service.build_generation_request(
            ctx, built, expected_output_type=FindingExplanation
        )
        session = service.create_session(request)
        assert session.provider.name() == "gemini"
        assert session.request.expected_output_type is FindingExplanation
        assert session.request.options.json_mode is True

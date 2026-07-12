"""Sprint 21.2 — generation_id traceability and AIFeature contracts."""

from __future__ import annotations

import os
from types import SimpleNamespace
from typing import Any
from uuid import UUID, uuid4

import pytest
from openai import OpenAIError

from app.ai.builders import FindingExplanationBuilder
from app.ai.cache import NullAICache, build_cache_key
from app.ai.config import AISettings, clear_ai_settings_cache
from app.ai.constants import SCHEMA_VERSION_FINDING_EXPLANATION
from app.ai.context import AIContext, FindingContext, WebsiteContext
from app.ai.exceptions import ServiceNotReady
from app.ai.factory import ProviderFactory
from app.ai.features import (
    AIFeature,
    FEATURE_PROMPT_IDS,
    GenerationId,
    prompt_id_for,
    resolve_feature,
)
from app.ai.openai_settings import OpenAISettings, clear_openai_settings_cache
from app.ai.prompt_repository import PromptRepository
from app.ai.providers.openai_provider import OpenAIProvider
from app.ai.registry import ProviderRegistry, reset_provider_registry
from app.ai.schemas import FindingExplanation
from app.ai.service import AIService


@pytest.fixture(autouse=True)
def _reset(monkeypatch: pytest.MonkeyPatch) -> None:
    clear_ai_settings_cache()
    clear_openai_settings_cache()
    reset_provider_registry()
    for key in list(os.environ):
        if key.startswith("AI_") or key.startswith("OPENAI_"):
            monkeypatch.delenv(key, raising=False)
    monkeypatch.setenv("OPENAI_API_KEY", "sk-test")
    monkeypatch.setenv("OPENAI_MODEL", "gpt-5.5")
    clear_ai_settings_cache()
    clear_openai_settings_cache()
    yield
    clear_ai_settings_cache()
    clear_openai_settings_cache()
    reset_provider_registry()


def _ctx() -> AIContext:
    return AIContext(
        audit_id=uuid4(),
        report_hash="rh-trace",
        schema_version=SCHEMA_VERSION_FINDING_EXPLANATION,
        website=WebsiteContext(url="https://example.com"),
        finding=FindingContext(
            finding_id="seo.title.missing",
            title="Missing title",
            severity="high",
            category="seo",
        ),
    )


def _valid() -> FindingExplanation:
    return FindingExplanation(
        finding_id="seo.title.missing",
        title="Missing document title",
        explanation="The page has no title element.",
        why_it_matters="Hurts CTR.",
        suggested_fix_summary="Add a title tag.",
        severity="high",
        category="seo",
    )


class _FakeResponses:
    def __init__(self, *, parsed: Any) -> None:
        self._parsed = parsed
        self.calls = 0

    async def parse(self, **kwargs: Any) -> Any:
        self.calls += 1
        return SimpleNamespace(
            id="resp_trace",
            output_parsed=self._parsed,
            output_text=None,
            usage=SimpleNamespace(input_tokens=5, output_tokens=9),
            status="completed",
            system_fingerprint="fp",
        )


class _FakeClient:
    def __init__(self, responses: _FakeResponses) -> None:
        self.responses = responses
        self.chat = SimpleNamespace(
            completions=SimpleNamespace(
                parse=lambda **kwargs: (_ for _ in ()).throw(OpenAIError("unused"))
            )
        )


def _service(client: _FakeClient) -> AIService:
    settings = AISettings(cache_enabled=False)
    provider = OpenAIProvider(
        model="gpt-5.5",
        api_key="sk-test",
        settings=OpenAISettings(OPENAI_API_KEY="sk-test", OPENAI_MODEL="gpt-5.5"),
        client=client,  # type: ignore[arg-type]
    )
    registry = ProviderRegistry()
    registry.register("openai", provider, set_as_default=True)
    return AIService(
        settings=settings,
        registry=registry,
        factory=ProviderFactory(settings),
        prompts=PromptRepository(),
        cache=NullAICache(),
    )


class TestAIFeatureEnum:
    def test_resolve_feature_accepts_enum_value_and_prompt_id(self) -> None:
        assert resolve_feature(AIFeature.FINDING) is AIFeature.FINDING
        assert resolve_feature("finding") is AIFeature.FINDING
        assert resolve_feature("finding_explanation") is AIFeature.FINDING
        assert prompt_id_for(AIFeature.FINDING) == "finding_explanation"
        assert FEATURE_PROMPT_IDS[AIFeature.RECOMMENDATION] == "recommendation"

    def test_builders_declare_feature(self) -> None:
        builder = FindingExplanationBuilder(PromptRepository())
        assert builder.feature is AIFeature.FINDING
        assert builder.prompt_id == "finding_explanation"
        built = builder.build(_ctx())
        assert built.diagnostics.feature is AIFeature.FINDING
        assert built.feature is AIFeature.FINDING

    def test_service_builder_registry_uses_enum(self) -> None:
        service = _service(_FakeClient(_FakeResponses(parsed=_valid())))
        assert service.get_builder(AIFeature.FINDING).feature is AIFeature.FINDING
        assert service.get_builder("finding_explanation").feature is AIFeature.FINDING
        assert service.get_builder("finding").feature is AIFeature.FINDING

    def test_provider_and_telemetry_store_feature(self) -> None:
        # Covered end-to-end in generation_id success path below.
        assert AIFeature.EXECUTIVE_SUMMARY.value == "executive_summary"

    def test_cache_key_unaffected_by_generation_id(self) -> None:
        built = FindingExplanationBuilder(PromptRepository()).build(_ctx())
        a = build_cache_key(
            provider="openai",
            model="gpt-5.5",
            schema_version=built.schema_version,
            builder_version=built.builder_version,
            prompt_version=f"{built.prompt_id}@{built.prompt_version}",
            locale="en",
            report_hash="rh-trace",
            entity_id="seo.title.missing",
            input_hash=built.input_hash,
        )
        b = build_cache_key(
            provider="openai",
            model="gpt-5.5",
            schema_version=built.schema_version,
            builder_version=built.builder_version,
            prompt_version=f"{built.prompt_id}@{built.prompt_version}",
            locale="en",
            report_hash="rh-trace",
            entity_id="seo.title.missing",
            input_hash=built.input_hash,
        )
        assert a == b
        assert "generation" not in a.lower()


class TestGenerationId:
    def test_generated_once_on_start_and_immutable(self) -> None:
        service = _service(_FakeClient(_FakeResponses(parsed=_valid())))
        session = service._prepare_session(
            feature=AIFeature.FINDING,
            context=_ctx(),
            expected_output_type=FindingExplanation,
            provider="openai",
            options=None,
        )
        with pytest.raises(ServiceNotReady):
            _ = session.generation_id
        session.start()
        gid = session.generation_id
        assert isinstance(gid, UUID)
        assert isinstance(gid, GenerationId)
        assert session.telemetry is not None
        assert session.telemetry.generation_id == gid
        assert session.telemetry.feature is AIFeature.FINDING
        with pytest.raises(ServiceNotReady):
            session.start()
        assert session.generation_id == gid

    def test_unique_across_sessions(self) -> None:
        service = _service(_FakeClient(_FakeResponses(parsed=_valid())))
        s1 = service._prepare_session(
            feature=AIFeature.FINDING,
            context=_ctx(),
            expected_output_type=FindingExplanation,
            provider="openai",
            options=None,
        )
        s2 = service._prepare_session(
            feature=AIFeature.FINDING,
            context=_ctx(),
            expected_output_type=FindingExplanation,
            provider="openai",
            options=None,
        )
        s1.start()
        s2.start()
        assert s1.generation_id != s2.generation_id

    @pytest.mark.asyncio
    async def test_propagated_to_response_telemetry_and_provider_metadata(self) -> None:
        client = _FakeClient(_FakeResponses(parsed=_valid()))
        service = _service(client)
        response = await service.explain_finding(_ctx())
        assert response.generation_id is not None
        assert response.provider_metadata.generation_id == response.generation_id
        assert response.telemetry is not None
        assert response.telemetry.generation_id == response.generation_id
        assert response.provider_metadata.feature is AIFeature.FINDING
        assert response.telemetry.feature is AIFeature.FINDING
        assert response.diagnostics is not None
        assert response.diagnostics.feature is AIFeature.FINDING
        assert response.quality is not None
        assert response.quality.feature is AIFeature.FINDING
        assert response.provider_metadata.request_id == str(response.generation_id)

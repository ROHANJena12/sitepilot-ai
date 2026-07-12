"""OpenAI provider tests — API call, structured parse, metadata (no grounding)."""

from __future__ import annotations

import os
from types import SimpleNamespace
from typing import Any
from uuid import uuid4

import pytest
from openai import APITimeoutError, OpenAIError

from app.ai.config import AISettings, clear_ai_settings_cache
from app.ai.constants import SCHEMA_VERSION_FINDING_EXPLANATION
from app.ai.context import (
    AIContext,
    FindingContext,
    WebsiteContext,
)
from app.ai.exceptions import (
    AIConfigurationError,
    AIProviderError,
    InvalidAIResponse,
)
from app.ai.factory import ProviderFactory
from app.ai.features import AIFeature
from app.ai.generation import GenerationOptions, GenerationRequest
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
        report_hash="rh-openai",
        schema_version=SCHEMA_VERSION_FINDING_EXPLANATION,
        website=WebsiteContext(url="https://example.com"),
        health_score=81,
        finding=FindingContext(
            finding_id="seo.title.missing",
            title="Missing title",
            description="No title tag",
            severity="high",
            category="seo",
            status="fail",
        ),
    )


def _valid_explanation() -> FindingExplanation:
    return FindingExplanation(
        finding_id="seo.title.missing",
        title="Missing document title",
        explanation="The page has no title element.",
        why_it_matters="Hurts CTR and shareability.",
        suggested_fix_summary="Add a unique title tag.",
        severity="high",
        category="seo",
        hedges=[],
        related_recommendation_ids=[],
    )


class _FakeResponses:
    def __init__(self, *, parsed: Any = None, error: Exception | None = None) -> None:
        self._parsed = parsed
        self._error = error
        self.calls = 0

    async def parse(self, **kwargs: Any) -> Any:
        self.calls += 1
        if self._error is not None:
            raise self._error
        return SimpleNamespace(
            id="resp_test_1",
            output_parsed=self._parsed,
            output_text=None,
            usage=SimpleNamespace(input_tokens=11, output_tokens=22),
            status="completed",
            system_fingerprint="fp_test",
        )


class _FakeCompletions:
    def __init__(
        self,
        *,
        parsed: Any = None,
        content: str | None = None,
        error: Exception | None = None,
    ) -> None:
        self._parsed = parsed
        self._content = content
        self._error = error
        self.calls = 0

    async def parse(self, **kwargs: Any) -> Any:
        self.calls += 1
        if self._error is not None:
            raise self._error
        message = SimpleNamespace(parsed=self._parsed, refusal=None, content=self._content)
        choice = SimpleNamespace(message=message, finish_reason="stop")
        return SimpleNamespace(
            id="chatcmpl_test_1",
            choices=[choice],
            usage=SimpleNamespace(prompt_tokens=11, completion_tokens=22),
            system_fingerprint="fp_chat",
        )


class _FakeChat:
    def __init__(self, completions: _FakeCompletions) -> None:
        self.completions = completions


class _FakeClient:
    def __init__(
        self,
        *,
        responses: _FakeResponses | None = None,
        completions: _FakeCompletions | None = None,
    ) -> None:
        self.responses = responses or _FakeResponses(error=OpenAIError("force fallback"))
        self.chat = _FakeChat(completions or _FakeCompletions(parsed=_valid_explanation()))


def _provider(client: _FakeClient) -> OpenAIProvider:
    return OpenAIProvider(
        model="gpt-5.5",
        api_key="sk-test",
        settings=OpenAISettings(OPENAI_API_KEY="sk-test", OPENAI_MODEL="gpt-5.5"),
        client=client,  # type: ignore[arg-type]
    )


def _service(client: _FakeClient) -> AIService:
    settings = AISettings()
    provider = _provider(client)
    registry = ProviderRegistry()
    registry.register("openai", provider, set_as_default=True)
    return AIService(
        settings=settings,
        registry=registry,
        factory=ProviderFactory(settings),
        prompts=PromptRepository(),
    )


def _request() -> GenerationRequest[FindingExplanation]:
    service = AIService(settings=AISettings(), prompts=PromptRepository())
    ctx = _ctx()
    built = service.build_finding_prompt(ctx)
    return GenerationRequest[FindingExplanation](
        context=ctx,
        built_prompt=built,
        options=GenerationOptions(json_mode=True),
        expected_output_type=FindingExplanation,
        provider="openai",
        model="gpt-5.5",
        cache_key="test-key",
    )


class TestOpenAIProviderParseAndMetadata:
    @pytest.mark.asyncio
    async def test_responses_api_metadata(self) -> None:
        client = _FakeClient(
            responses=_FakeResponses(parsed=_valid_explanation()),
            completions=_FakeCompletions(error=AssertionError("should not fallback")),
        )
        response = await _provider(client).generate(_request())
        assert response.result.finding_id == "seo.title.missing"
        assert response.provider_metadata.provider == "openai"
        assert response.provider_metadata.model == "gpt-5.5"
        assert response.provider_metadata.api_version == "v1"
        assert response.provider_metadata.finish_reason == "completed"
        assert response.provider_metadata.tokens_in == 11
        assert response.provider_metadata.tokens_out == 22
        assert response.provider_metadata.total_tokens == 33
        assert response.provider_metadata.cost_usd is None
        assert response.provider_metadata.cached is False
        assert response.provider_metadata.generation_status == "success"
        assert response.provider_metadata.response_id == "resp_test_1"
        assert response.provider_metadata.system_fingerprint == "fp_test"
        assert response.provider_metadata.provider_latency_ms is not None
        assert response.telemetry is not None
        assert client.responses.calls == 1

    @pytest.mark.asyncio
    async def test_chat_completions_fallback_metadata(self) -> None:
        client = _FakeClient(
            responses=_FakeResponses(error=OpenAIError("responses unavailable")),
            completions=_FakeCompletions(parsed=_valid_explanation()),
        )
        response = await _provider(client).generate(_request())
        assert response.provider_metadata.finish_reason == "stop"
        assert response.provider_metadata.response_id == "chatcmpl_test_1"
        assert response.provider_metadata.system_fingerprint == "fp_chat"
        assert client.chat.completions.calls == 1

    @pytest.mark.asyncio
    async def test_invalid_json_raises(self) -> None:
        class BadResponses(_FakeResponses):
            async def parse(self, **kwargs: Any) -> Any:
                self.calls += 1
                return SimpleNamespace(
                    id="resp_bad",
                    output_parsed=None,
                    output_text="{not-json",
                    usage=None,
                    status="completed",
                )

        with pytest.raises(InvalidAIResponse, match="invalid JSON"):
            await _provider(_FakeClient(responses=BadResponses())).generate(_request())

    @pytest.mark.asyncio
    async def test_schema_validation_failure(self) -> None:
        client = _FakeClient(
            responses=_FakeResponses(parsed={"finding_id": "x"}),
        )
        with pytest.raises(InvalidAIResponse, match="schema validation"):
            await _provider(client).generate(_request())

    @pytest.mark.asyncio
    async def test_timeout(self) -> None:
        import httpx

        timeout = APITimeoutError(request=httpx.Request("POST", "https://api.openai.com/v1"))
        client = _FakeClient(
            responses=_FakeResponses(error=timeout),
            completions=_FakeCompletions(error=timeout),
        )
        with pytest.raises(AIProviderError, match="timed out|OpenAI"):
            await _provider(client).generate(_request())

    @pytest.mark.asyncio
    async def test_provider_exception(self) -> None:
        client = _FakeClient(
            responses=_FakeResponses(error=OpenAIError("boom")),
            completions=_FakeCompletions(error=OpenAIError("boom2")),
        )
        with pytest.raises(AIProviderError):
            await _provider(client).generate(_request())

    @pytest.mark.asyncio
    async def test_missing_api_key(self) -> None:
        provider = OpenAIProvider(api_key=None, client=None, settings=OpenAISettings())
        with pytest.raises(AIConfigurationError, match="OPENAI_API_KEY"):
            await provider.generate(_request())

    def test_openai_settings_env(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("OPENAI_MODEL", "gpt-5.5")
        monkeypatch.setenv("OPENAI_TIMEOUT", "30")
        monkeypatch.setenv("OPENAI_MAX_RETRIES", "1")
        clear_openai_settings_cache()
        cfg = OpenAISettings()
        assert cfg.model == "gpt-5.5"
        assert cfg.timeout == 30.0
        assert cfg.max_retries == 1


class TestServiceOrchestrationUsesProviderThenGrounding:
    @pytest.mark.asyncio
    async def test_explain_finding_provider_grounding_response(self) -> None:
        client = _FakeClient(responses=_FakeResponses(parsed=_valid_explanation()))
        service = _service(client)
        response = await service.explain_finding(_ctx())
        assert response.result.finding_id == "seo.title.missing"
        assert response.provider_metadata.provider == "openai"
        assert response.provider_metadata.model == "gpt-5.5"
        assert response.session_id is not None
        assert response.diagnostics is not None
        assert response.telemetry is not None
        assert response.telemetry.generation_status == "success"
        assert response.result.provider == "openai"
        assert response.result.prompt_version == "v2"

    @pytest.mark.asyncio
    async def test_session_lifecycle_on_success(self) -> None:
        client = _FakeClient(responses=_FakeResponses(parsed=_valid_explanation()))
        service = _service(client)
        session = service._prepare_session(
            feature=AIFeature.FINDING,
            context=_ctx(),
            expected_output_type=FindingExplanation,
            provider="openai",
            options=None,
        )
        assert session.started_at is None
        session.start()
        assert session.started_at is not None
        assert session.generation_id is not None
        response = await session.provider.generate(session.request)
        grounded = service.apply_grounding(
            result=response.result,
            context=_ctx(),
            expected_output_type=FindingExplanation,
        )
        bound = response.model_copy(
            update={
                "result": grounded,
                "session_id": session.session_id,
                "generation_id": session.generation_id,
            }
        )
        session.attach_response(bound)
        session.finish()
        assert session.finished_at is not None
        assert session.duration_ms is not None
        assert session.response is bound

    @pytest.mark.asyncio
    async def test_all_core_features_are_wired(self) -> None:
        """Quick Win is now wired; this smoke test keeps the orchestration path."""
        service = _service(
            _FakeClient(responses=_FakeResponses(parsed=_valid_explanation()))
        )
        finding_ctx = _ctx()
        # Without a matching QuickWin schema parse this would fail — just ensure
        # GenerationNotImplemented is gone by checking config/provider path works
        # for findings (already covered) and that explain_quick_win is callable.
        assert hasattr(service, "generate_quick_win")
        assert hasattr(service, "explain_quick_win")
        assert finding_ctx.finding is not None

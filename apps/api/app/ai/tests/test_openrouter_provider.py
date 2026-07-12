"""OpenRouter provider tests — mocked HTTP, no real API calls."""

from __future__ import annotations

import json
import os
from types import SimpleNamespace
from typing import Any
from unittest.mock import MagicMock
from uuid import uuid4

import pytest
from openai import APITimeoutError, OpenAIError, RateLimitError
from pydantic import ValidationError

from app.ai.config import AISettings, clear_ai_settings_cache
from app.ai.constants import (
    DEFAULT_OPENROUTER_MODEL,
    PROVIDER_OPENROUTER,
    SCHEMA_VERSION_FINDING_EXPLANATION,
)
from app.ai.context import AIContext, FindingContext, WebsiteContext
from app.ai.exceptions import (
    AIConfigurationError,
    AIProviderError,
    InvalidAIResponse,
)
from app.ai.factory import ProviderFactory
from app.ai.generation import GenerationOptions, GenerationRequest
from app.ai.openrouter_settings import (
    OpenRouterSettings,
    clear_openrouter_settings_cache,
)
from app.ai.prompt_repository import PromptRepository
from app.ai.providers.openrouter_diagnostics import (
    build_provider_diagnostics,
    classify_content_type,
    recover_text_from_validation_error,
    truncate_preview,
)
from app.ai.providers.openrouter_provider import (
    JSON_ONLY_RECOVERY_INSTRUCTION,
    OpenRouterProvider,
)
from app.ai.providers.structured_output import (
    _coerce_json_text,
    parse_structured_payload,
)
from app.ai.registry import ProviderRegistry, reset_provider_registry
from app.ai.schemas import FindingExplanation
from app.ai.service import AIService


@pytest.fixture(autouse=True)
def _reset(monkeypatch: pytest.MonkeyPatch) -> None:
    clear_ai_settings_cache()
    clear_openrouter_settings_cache()
    reset_provider_registry()
    for key in list(os.environ):
        if (
            key.startswith("AI_")
            or key.startswith("OPENAI_")
            or key.startswith("OPENROUTER_")
        ):
            monkeypatch.delenv(key, raising=False)
    monkeypatch.setenv("OPENROUTER_API_KEY", "or-test-key")
    monkeypatch.setenv("OPENROUTER_MODEL", DEFAULT_OPENROUTER_MODEL)
    clear_ai_settings_cache()
    clear_openrouter_settings_cache()
    yield
    clear_ai_settings_cache()
    clear_openrouter_settings_cache()
    reset_provider_registry()


def _ctx() -> AIContext:
    return AIContext(
        audit_id=uuid4(),
        report_hash="rh-openrouter",
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


def _valid_json() -> str:
    return json.dumps(_valid_explanation().model_dump(mode="json"))


def _rate_limit_error(message: str = "Rate limit exceeded") -> RateLimitError:
    response = MagicMock()
    response.status_code = 429
    response.headers = {}
    response.request = MagicMock()
    return RateLimitError(
        message, response=response, body={"error": {"message": message}}
    )


def _validation_error_with_input(raw: str) -> ValidationError:
    return ValidationError.from_exception_data(
        "FindingExplanation",
        [
            {
                "type": "json_invalid",
                "loc": (),
                "input": raw,
                "ctx": {"error": "expected value at line 1 column 1"},
            }
        ],
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
            id="or_resp_1",
            output_parsed=self._parsed,
            output_text=None,
            usage=SimpleNamespace(input_tokens=9, output_tokens=18),
            status="completed",
            system_fingerprint="fp_or",
        )


class _FakeCompletions:
    def __init__(
        self,
        *,
        parsed: Any = None,
        content: str | None = None,
        parse_content: str | None = None,
        parse_error: Exception | None = None,
        create_error: Exception | None = None,
        create_queue: list[str | None] | None = None,
    ) -> None:
        self._parsed = parsed
        self._content = content
        self._parse_content = parse_content
        self._parse_error = parse_error
        self._create_error = create_error
        self._create_queue = list(create_queue) if create_queue is not None else None
        self.parse_calls = 0
        self.create_calls = 0
        self.create_kwargs: list[dict[str, Any]] = []

    async def parse(self, **kwargs: Any) -> Any:
        self.parse_calls += 1
        if self._parse_error is not None:
            raise self._parse_error
        message = SimpleNamespace(
            parsed=self._parsed,
            refusal=None,
            content=self._parse_content,
        )
        choice = SimpleNamespace(message=message, finish_reason="stop")
        return SimpleNamespace(
            id="or_chat_1",
            choices=[choice],
            usage=SimpleNamespace(prompt_tokens=9, completion_tokens=18),
            system_fingerprint="fp_or_chat",
        )

    async def create(self, **kwargs: Any) -> Any:
        self.create_calls += 1
        self.create_kwargs.append(kwargs)
        if self._create_error is not None and (
            self._create_queue is None or not self._create_queue
        ):
            raise self._create_error
        if self._create_queue is not None:
            if not self._create_queue:
                raise OpenAIError("create_queue exhausted")
            content = self._create_queue.pop(0)
        else:
            content = self._content
        message = SimpleNamespace(content=content, refusal=None)
        choice = SimpleNamespace(message=message, finish_reason="stop")
        return SimpleNamespace(
            id=f"or_chat_create_{self.create_calls}",
            choices=[choice],
            usage=SimpleNamespace(prompt_tokens=5, completion_tokens=7),
            system_fingerprint=None,
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
        self.chat = _FakeChat(
            completions or _FakeCompletions(parsed=_valid_explanation())
        )
        self.base_url = "https://openrouter.ai/api/v1"


def _provider(client: _FakeClient) -> OpenRouterProvider:
    return OpenRouterProvider(
        model=DEFAULT_OPENROUTER_MODEL,
        api_key="or-test",
        settings=OpenRouterSettings(
            OPENROUTER_API_KEY="or-test",
            OPENROUTER_MODEL=DEFAULT_OPENROUTER_MODEL,
        ),
        client=client,  # type: ignore[arg-type]
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
        provider="openrouter",
        model=DEFAULT_OPENROUTER_MODEL,
        cache_key="or-test-key",
    )


class TestOpenRouterConfiguration:
    def test_settings_defaults(self) -> None:
        cfg = OpenRouterSettings(
            OPENROUTER_API_KEY="k",
            OPENROUTER_MODEL="openai/gpt-oss-20b:free",
        )
        assert cfg.base_url == "https://openrouter.ai/api/v1"
        assert cfg.model == "openai/gpt-oss-20b:free"

    def test_missing_key_raises_on_client(self) -> None:
        provider = OpenRouterProvider(
            api_key=None,
            settings=OpenRouterSettings(OPENROUTER_API_KEY=None),
        )
        with pytest.raises(AIConfigurationError, match="OPENROUTER_API_KEY"):
            provider._get_client()

    @pytest.mark.asyncio
    async def test_health_without_key(self) -> None:
        provider = OpenRouterProvider(
            api_key=None,
            settings=OpenRouterSettings(OPENROUTER_API_KEY=None),
        )
        health = await provider.health()
        assert health.healthy is False
        assert health.provider == "openrouter"


class TestOpenRouterFactoryAndRegistry:
    def test_factory_creates_openrouter(self) -> None:
        settings = AISettings(default_provider="openrouter")
        factory = ProviderFactory(settings)
        provider = factory.create("openrouter")
        assert provider.name() == "openrouter"
        assert isinstance(provider, OpenRouterProvider)

    def test_populate_registry_includes_openrouter(self) -> None:
        factory = ProviderFactory(AISettings())
        registry = factory.populate_registry()
        assert "openrouter" in registry.list()
        assert set(factory.available()) >= {
            "openai",
            "openrouter",
            "anthropic",
            "gemini",
            "ollama",
        }

    def test_default_provider_switch(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("AI_DEFAULT_PROVIDER", "openrouter")
        monkeypatch.setenv("AI_OPENROUTER_MODEL", "openai/gpt-oss-20b:free")
        clear_ai_settings_cache()
        settings = AISettings()
        assert settings.default_provider == PROVIDER_OPENROUTER
        factory = ProviderFactory(settings)
        assert factory.create_default().name() == "openrouter"


class TestOpenRouterProviderGenerate:
    @pytest.mark.asyncio
    async def test_responses_api_metadata(self) -> None:
        client = _FakeClient(
            responses=_FakeResponses(parsed=_valid_explanation()),
            completions=_FakeCompletions(
                parse_error=AssertionError("should not fallback")
            ),
        )
        response = await _provider(client).generate(_request())
        assert response.result.finding_id == "seo.title.missing"
        assert response.provider_metadata.provider == "openrouter"
        assert response.provider_metadata.model == DEFAULT_OPENROUTER_MODEL
        assert response.provider_metadata.finish_reason == "completed"
        assert response.provider_metadata.tokens_in == 9
        assert response.provider_metadata.tokens_out == 18
        assert response.provider_metadata.response_id == "or_resp_1"
        assert response.provider_metadata.cached is False
        assert response.telemetry is not None
        assert response.telemetry.provider == "openrouter"
        assert response.telemetry.latency_ms is not None
        assert client.chat.completions.parse_calls == 0
        assert client.chat.completions.create_calls == 0

    @pytest.mark.asyncio
    async def test_chat_parse_fallback(self) -> None:
        client = _FakeClient(
            responses=_FakeResponses(error=OpenAIError("no responses")),
            completions=_FakeCompletions(parsed=_valid_explanation()),
        )
        response = await _provider(client).generate(_request())
        assert response.provider_metadata.provider == "openrouter"
        assert response.provider_metadata.response_id == "or_chat_1"
        assert client.chat.completions.create_calls == 0

    @pytest.mark.asyncio
    async def test_json_create_fallback(self) -> None:
        client = _FakeClient(
            responses=_FakeResponses(error=OpenAIError("no responses")),
            completions=_FakeCompletions(
                parse_error=OpenAIError("no parse"),
                content=_valid_json(),
            ),
        )
        response = await _provider(client).generate(_request())
        assert response.result.severity == "high"
        assert response.provider_metadata.response_id == "or_chat_create_1"
        assert client.chat.completions.create_calls == 1

    @pytest.mark.asyncio
    async def test_timeout_raises_immediately_on_responses(self) -> None:
        client = _FakeClient(
            responses=_FakeResponses(error=APITimeoutError(request=None)),  # type: ignore[arg-type]
            completions=_FakeCompletions(parsed=_valid_explanation()),
        )
        with pytest.raises(AIProviderError, match="timed out"):
            await _provider(client).generate(_request())
        assert client.chat.completions.parse_calls == 0
        assert client.chat.completions.create_calls == 0

    @pytest.mark.asyncio
    async def test_timeout_on_chat_parse(self) -> None:
        client = _FakeClient(
            responses=_FakeResponses(error=OpenAIError("no responses")),
            completions=_FakeCompletions(
                parse_error=APITimeoutError(request=None),  # type: ignore[arg-type]
            ),
        )
        with pytest.raises(AIProviderError, match="timed out") as caught:
            await _provider(client).generate(_request())
        assert client.chat.completions.create_calls == 0
        assert caught.value.diagnostics is not None
        assert caught.value.diagnostics["error_type"] == "APITimeoutError"
        assert "chat.parse" in caught.value.diagnostics["stage_latency_ms"]

    @pytest.mark.asyncio
    async def test_rate_limit_raises_immediately(self) -> None:
        client = _FakeClient(
            responses=_FakeResponses(error=_rate_limit_error()),
            completions=_FakeCompletions(parsed=_valid_explanation()),
        )
        with pytest.raises(AIProviderError, match="rate limit \\(429\\)") as caught:
            await _provider(client).generate(_request())
        assert client.chat.completions.parse_calls == 0
        assert caught.value.diagnostics is not None
        assert caught.value.diagnostics["status_code"] == 429

    @pytest.mark.asyncio
    async def test_provider_failure(self) -> None:
        client = _FakeClient(
            responses=_FakeResponses(error=OpenAIError("upstream")),
            completions=_FakeCompletions(
                parse_error=OpenAIError("upstream"),
                create_error=OpenAIError("upstream boom"),
            ),
        )
        with pytest.raises(AIProviderError, match="OpenRouter"):
            await _provider(client).generate(_request())

    @pytest.mark.asyncio
    async def test_empty_chat_parse_falls_back_to_json_object(self) -> None:
        """OpenRouter .parse() may return HTTP 200 with parsed=None/content=None."""
        client = _FakeClient(
            responses=_FakeResponses(error=OpenAIError("no responses")),
            completions=_FakeCompletions(
                parsed=None,
                parse_content=None,
                content=_valid_json(),
            ),
        )
        response = await _provider(client).generate(_request())
        assert response.result.finding_id == "seo.title.missing"
        assert client.chat.completions.parse_calls == 1
        assert client.chat.completions.create_calls == 1

    @pytest.mark.asyncio
    async def test_empty_content(self) -> None:
        client = _FakeClient(
            responses=_FakeResponses(error=OpenAIError("no responses")),
            completions=_FakeCompletions(
                parse_error=OpenAIError("no parse"),
                create_queue=["", ""],
            ),
        )
        with pytest.raises(
            InvalidAIResponse, match="empty structured payload"
        ) as caught:
            await _provider(client).generate(_request())
        assert client.chat.completions.create_calls == 2
        assert caught.value.diagnostics is not None
        assert caught.value.diagnostics["recovery_attempt"] is True

    @pytest.mark.asyncio
    async def test_invalid_json(self) -> None:
        client = _FakeClient(
            responses=_FakeResponses(error=OpenAIError("no responses")),
            completions=_FakeCompletions(
                parse_error=OpenAIError("no parse"),
                # First create: malformed; recovery also malformed → fail once.
                create_queue=["{not-json", "{still-not-json"],
            ),
        )
        with pytest.raises(InvalidAIResponse, match="invalid JSON") as caught:
            await _provider(client).generate(_request())
        assert client.chat.completions.create_calls == 2
        assert caught.value.diagnostics is not None
        assert caught.value.diagnostics["recovery_attempt"] is True
        assert caught.value.diagnostics["recovery_reason"] == "invalid_json"

    @pytest.mark.asyncio
    async def test_validation_error_recovers_fenced_json(self) -> None:
        fenced = "```json\n" + _valid_json() + "\n```"
        client = _FakeClient(
            responses=_FakeResponses(error=OpenAIError("no responses")),
            completions=_FakeCompletions(
                parse_error=_validation_error_with_input(fenced),
                content="should-not-be-used",
            ),
        )
        response = await _provider(client).generate(_request())
        assert response.result.finding_id == "seo.title.missing"
        assert client.chat.completions.create_calls == 0

    @pytest.mark.asyncio
    async def test_validation_error_recovers_plain_json(self) -> None:
        client = _FakeClient(
            responses=_FakeResponses(error=OpenAIError("no responses")),
            completions=_FakeCompletions(
                parse_error=_validation_error_with_input(_valid_json()),
            ),
        )
        response = await _provider(client).generate(_request())
        assert response.result.severity == "high"
        assert client.chat.completions.create_calls == 0

    @pytest.mark.asyncio
    async def test_validation_error_unrecoverable_raises_invalid_json(self) -> None:
        client = _FakeClient(
            responses=_FakeResponses(error=OpenAIError("no responses")),
            completions=_FakeCompletions(
                parse_error=_validation_error_with_input("not-json-at-all"),
                create_queue=["still not json", "\\begin{document}nope"],
            ),
        )
        with pytest.raises(InvalidAIResponse, match="invalid JSON") as caught:
            await _provider(client).generate(_request())
        # Cascade continues to json_object, then one recovery create.
        assert client.chat.completions.create_calls == 2
        assert caught.value.diagnostics is not None
        assert caught.value.diagnostics["recovery_attempt"] is True

    @pytest.mark.asyncio
    async def test_stage_latency_measured_on_success(self) -> None:
        client = _FakeClient(
            responses=_FakeResponses(parsed=_valid_explanation()),
            completions=_FakeCompletions(
                parse_error=AssertionError("should not fallback")
            ),
        )
        response = await _provider(client).generate(_request())
        assert response.telemetry is not None
        assert response.telemetry.provider_latency_ms is not None
        assert response.telemetry.prompt_build_latency_ms is not None

    @pytest.mark.asyncio
    async def test_latex_output_triggers_json_recovery(self) -> None:
        latex = r"\begin{document}\textbf{Executive Summary} score is fine\end{document}"
        client = _FakeClient(
            responses=_FakeResponses(error=OpenAIError("no responses")),
            completions=_FakeCompletions(
                parse_error=OpenAIError("no parse"),
                create_queue=[latex, _valid_json()],
            ),
        )
        response = await _provider(client).generate(_request())
        assert response.result.finding_id == "seo.title.missing"
        assert client.chat.completions.create_calls == 2
        assert response.provider_metadata.retry_count == 1
        recovery_kwargs = client.chat.completions.create_kwargs[1]
        system = recovery_kwargs["messages"][0]["content"]
        assert JSON_ONLY_RECOVERY_INSTRUCTION in system
        assert system.strip().endswith("'{'.") or "first character" in system

    @pytest.mark.asyncio
    async def test_markdown_output_triggers_json_recovery(self) -> None:
        md = "# Executive Summary\n\nThe site looks **okay** overall."
        client = _FakeClient(
            responses=_FakeResponses(error=OpenAIError("no responses")),
            completions=_FakeCompletions(
                parse_error=OpenAIError("no parse"),
                create_queue=[md, _valid_json()],
            ),
        )
        response = await _provider(client).generate(_request())
        assert response.result.severity == "high"
        assert client.chat.completions.create_calls == 2

    @pytest.mark.asyncio
    async def test_fenced_json_does_not_need_recovery(self) -> None:
        fenced = "```json\n" + _valid_json() + "\n```"
        client = _FakeClient(
            responses=_FakeResponses(error=OpenAIError("no responses")),
            completions=_FakeCompletions(
                parse_error=OpenAIError("no parse"),
                content=fenced,
            ),
        )
        response = await _provider(client).generate(_request())
        assert response.result.finding_id == "seo.title.missing"
        assert client.chat.completions.create_calls == 1
        assert response.provider_metadata.retry_count == 0

    @pytest.mark.asyncio
    async def test_explanatory_prose_triggers_json_recovery(self) -> None:
        prose = "Sure, here is a summary of the audit in plain English without JSON."
        client = _FakeClient(
            responses=_FakeResponses(error=OpenAIError("no responses")),
            completions=_FakeCompletions(
                parse_error=OpenAIError("no parse"),
                create_queue=[prose, _valid_json()],
            ),
        )
        response = await _provider(client).generate(_request())
        assert response.result.finding_id == "seo.title.missing"
        assert client.chat.completions.create_calls == 2

    @pytest.mark.asyncio
    async def test_recovery_failure_records_diagnostics(self) -> None:
        latex = r"\begin{document}\textbf{nope}\end{document}"
        client = _FakeClient(
            responses=_FakeResponses(error=OpenAIError("no responses")),
            completions=_FakeCompletions(
                parse_error=OpenAIError("no parse"),
                create_queue=[latex, latex],
            ),
        )
        with pytest.raises(InvalidAIResponse) as caught:
            await _provider(client).generate(_request())
        assert client.chat.completions.create_calls == 2
        diag = caught.value.diagnostics
        assert diag is not None
        assert diag["recovery_attempt"] is True
        assert diag["recovery_reason"] == "invalid_json"
        assert diag["original_content_type"] == "latex"
        assert "original_finish_reason" in diag


class TestOpenRouterDiagnosticsHelpers:
    def test_truncate_preview(self) -> None:
        assert truncate_preview(None) is None
        assert truncate_preview("  hi  ") == "hi"
        long = "x" * 600
        preview = truncate_preview(long, limit=20)
        assert preview is not None
        assert len(preview) == 20
        assert preview.endswith("...")

    def test_recover_text_from_validation_error(self) -> None:
        raw = '```json\n{"ok": true}\n```'
        exc = _validation_error_with_input(raw)
        assert recover_text_from_validation_error(exc) == raw

    def test_classify_content_type(self) -> None:
        assert classify_content_type(r"\begin{doc}\textbf{x}\end{doc}") == "latex"
        assert classify_content_type("# Title\n\n- item") == "markdown"
        assert classify_content_type('{"a":1}') == "json"
        assert classify_content_type("```json\n{}\n```") == "fenced_json"
        assert classify_content_type("Just an explanation.") == "prose"
        assert classify_content_type("") == "empty"

    def test_build_provider_diagnostics_bounded(self) -> None:
        diag = build_provider_diagnostics(
            provider="openrouter",
            model="openai/gpt-oss-20b:free",
            stage="chat.parse",
            status_code=429,
            error_type="RateLimitError",
            message="rate limited",
            raw_preview="x" * 2000,
            stage_latency_ms={"responses.parse": 10, "chat.parse": 20},
            total_provider_ms=30,
            recovery_attempt=True,
            recovery_reason="invalid_json",
            original_content_type="latex",
            original_finish_reason="stop",
        )
        assert diag["provider"] == "openrouter"
        assert diag["status_code"] == 429
        assert diag["raw_preview"] is not None
        assert len(diag["raw_preview"]) <= 512
        assert diag["stage_latency_ms"]["chat.parse"] == 20
        assert diag["recovery_attempt"] is True
        assert diag["original_content_type"] == "latex"


class TestSharedStructuredParse:
    def test_parse_dict(self) -> None:
        data = _valid_explanation().model_dump(mode="json")
        result = parse_structured_payload(
            parsed=data,
            raw_payload=None,
            output_type=FindingExplanation,
            provider_label="OpenRouter",
        )
        assert isinstance(result, FindingExplanation)

    def test_parse_markdown_fenced_json(self) -> None:
        fenced = "```json\n" + _valid_json() + "\n```"
        result = parse_structured_payload(
            parsed=fenced,
            raw_payload=None,
            output_type=FindingExplanation,
            provider_label="OpenRouter",
        )
        assert result.finding_id == "seo.title.missing"

    def test_coerce_trailing_markdown(self) -> None:
        payload = _valid_json() + "\n\nThanks!"
        data = _coerce_json_text(payload)
        assert data["finding_id"] == "seo.title.missing"

    def test_parse_invalid_raises(self) -> None:
        with pytest.raises(InvalidAIResponse):
            parse_structured_payload(
                parsed={"finding_id": "x"},
                raw_payload=None,
                output_type=FindingExplanation,
                provider_label="OpenRouter",
            )


class TestOpenRouterGroundingIntegration:
    @pytest.mark.asyncio
    async def test_aiservice_grounds_openrouter_output(self) -> None:
        client = _FakeClient(
            responses=_FakeResponses(parsed=_valid_explanation()),
        )
        settings = AISettings(default_provider="openrouter")
        provider = _provider(client)
        registry = ProviderRegistry()
        registry.register("openrouter", provider, set_as_default=True)
        service = AIService(
            settings=settings,
            registry=registry,
            factory=ProviderFactory(settings),
            prompts=PromptRepository(),
        )
        response = await service.explain_finding(_ctx(), provider="openrouter")
        assert response.quality is not None
        assert response.quality.grounded is True
        assert response.provider_metadata.provider == "openrouter"
        assert response.result.finding_id == "seo.title.missing"

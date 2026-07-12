"""OpenAI LLM provider — API call, structured parse, and metadata only."""

from __future__ import annotations

import time
from datetime import UTC, datetime
from typing import Any, TypeVar

from openai import APITimeoutError, AsyncOpenAI, OpenAIError
from pydantic import BaseModel

from app.ai.constants import DEFAULT_OPENAI_MODEL
from app.ai.exceptions import (
    AIConfigurationError,
    AIProviderError,
    InvalidAIResponse,
)
from app.ai.generation import GenerationRequest
from app.ai.models import ProviderHealth
from app.ai.openai_settings import OpenAISettings, get_openai_settings
from app.ai.provider_capabilities import ProviderCapabilities
from app.ai.providers.base import LLMProvider
from app.ai.providers.provider_enum import AIProvider
from app.ai.providers.structured_output import (
    parse_structured_payload,
    system_prompt_for,
)
from app.ai.response import AIResponse, ProviderResponseMetadata
from app.ai.telemetry import GenerationTelemetry

T = TypeVar("T")

_MISSING = object()


class OpenAIProvider(LLMProvider):
    """
    OpenAI adapter: HTTP + structured parse + provider metadata.

    Does not perform grounding or business validation — AIService owns that.
    """

    def __init__(
        self,
        *,
        model: str | None = None,
        api_key: str | None | object = _MISSING,
        timeout: float | None = None,
        max_retries: int | None = None,
        settings: OpenAISettings | None = None,
        client: AsyncOpenAI | None = None,
    ) -> None:
        cfg = settings or get_openai_settings()
        # Explicit ``api_key=None`` disables the key (does not fall back to env).
        self._api_key = cfg.api_key if api_key is _MISSING else api_key  # type: ignore[assignment]
        self._model = model or cfg.model or DEFAULT_OPENAI_MODEL
        self._timeout = float(timeout if timeout is not None else cfg.timeout)
        self._max_retries = int(max_retries if max_retries is not None else cfg.max_retries)
        self._client = client
        self._capabilities = ProviderCapabilities(
            provider_name=AIProvider.OPENAI,
            supports_json=True,
            supports_streaming=True,
            supports_function_calling=True,
            supports_vision=True,
            supports_system_messages=True,
            supports_temperature=True,
            supports_seed=True,
            max_context_tokens=128_000,
            max_output_tokens=16_384,
            supports_response_schema=True,
            supports_tools=True,
            supports_images=True,
            supports_audio=False,
            supports_parallel_calls=True,
        )

    def name(self) -> AIProvider:
        return AIProvider.OPENAI

    def vendor(self) -> str:
        return "OpenAI"

    def default_model(self) -> str:
        return DEFAULT_OPENAI_MODEL

    def api_version(self) -> str:
        return "v1"

    def model(self) -> str:
        return self._model

    def is_available(self) -> bool:
        """Configured when an API key is present (used by provider routing)."""
        return bool(self._api_key) or self._client is not None

    @property
    def capabilities(self) -> ProviderCapabilities:
        return self._capabilities

    def _get_client(self) -> AsyncOpenAI:
        if self._client is not None:
            return self._client
        if not self._api_key:
            raise AIConfigurationError(
                "OPENAI_API_KEY is not configured. Set it in the environment."
            )
        self._client = AsyncOpenAI(
            api_key=self._api_key,
            timeout=self._timeout,
            max_retries=self._max_retries,
        )
        return self._client

    async def health(self) -> ProviderHealth:
        return ProviderHealth(
            healthy=bool(self._api_key) or self._client is not None,
            provider=self.name(),
            model=self.model(),
            detail=(
                "API key configured"
                if (self._api_key or self._client is not None)
                else "OPENAI_API_KEY missing"
            ),
        )

    async def generate(self, request: GenerationRequest[T]) -> AIResponse[T]:
        output_type = request.expected_output_type
        if not issubclass(output_type, BaseModel):
            raise InvalidAIResponse(
                f"expected_output_type must be a Pydantic model, got {output_type!r}"
            )

        started = time.perf_counter()
        generated_at = datetime.now(UTC)

        try:
            (
                parsed,
                finish_reason,
                tokens_in,
                tokens_out,
                response_id,
                system_fingerprint,
                raw_payload,
            ) = await self._call_openai(
                request=request,
                output_type=output_type,
            )
        except APITimeoutError as exc:
            raise AIProviderError(f"OpenAI request timed out: {exc}") from exc
        except OpenAIError as exc:
            raise AIProviderError(f"OpenAI provider error: {exc}") from exc
        except AIConfigurationError:
            raise
        except InvalidAIResponse:
            raise
        except Exception as exc:  # noqa: BLE001
            raise AIProviderError(f"Unexpected OpenAI failure: {exc}") from exc

        provider_latency_ms = int((time.perf_counter() - started) * 1000)
        result = parse_structured_payload(
            parsed=parsed,
            raw_payload=raw_payload,
            output_type=output_type,
            provider_label="OpenAI",
        )

        total_tokens: int | None = None
        if tokens_in is not None or tokens_out is not None:
            total_tokens = (tokens_in or 0) + (tokens_out or 0)

        diagnostics = request.built_prompt.diagnostics.model_copy(
            update={
                "actual_tokens": (tokens_out if tokens_out is not None else None),
            }
        )
        feature = request.built_prompt.diagnostics.feature
        metadata = ProviderResponseMetadata(
            feature=feature,
            provider=self.name(),
            model=self.model(),
            api_version=self.api_version(),
            finish_reason=finish_reason,
            latency_ms=provider_latency_ms,
            provider_latency_ms=provider_latency_ms,
            tokens_in=tokens_in,
            tokens_out=tokens_out,
            total_tokens=total_tokens,
            cost_usd=None,
            cached=False,
            retry_count=0,
            generation_status="success",
            request_id=None,
            response_id=response_id,
            system_fingerprint=system_fingerprint,
        )
        telemetry = GenerationTelemetry(
            feature=feature,
            provider=self.name(),
            model=self.model(),
            prompt_version=request.prompt_version,
            schema_version=request.schema_version,
            builder_version=request.builder_version,
            cache_hit=False,
            cache_key=request.cache_key,
            report_hash=request.context.report_hash,
            latency_ms=provider_latency_ms,
            provider_latency_ms=provider_latency_ms,
            tokens_in=tokens_in,
            tokens_out=tokens_out,
            cost_usd=None,
            status="success",
            generation_status="success",
            finish_reason=finish_reason,
            retry_count=0,
            request_id=None,
            created_at=generated_at,
        )

        return AIResponse[T](
            result=result,  # type: ignore[arg-type]
            quality=None,
            provider_metadata=metadata,
            diagnostics=diagnostics,
            telemetry=telemetry,
            session_id=None,
            generated_at=generated_at,
        )

    async def _call_openai(
        self,
        *,
        request: GenerationRequest[T],
        output_type: type[BaseModel],
    ) -> tuple[
        BaseModel | dict[str, Any] | str | None,
        str | None,
        int | None,
        int | None,
        str | None,
        str | None,
        object,
    ]:
        client = self._get_client()
        user_content = request.rendered_text
        temperature = request.options.temperature
        max_tokens = request.options.max_output_tokens
        feature = request.built_prompt.diagnostics.feature
        system = system_prompt_for(feature, request.options.system_prompt)

        # Prefer Responses API structured parse.
        try:
            response = await client.responses.parse(
                model=self._model,
                instructions=system,
                input=user_content,
                text_format=output_type,
                temperature=temperature,
                max_output_tokens=max_tokens,
            )
            parsed = getattr(response, "output_parsed", None)
            usage = getattr(response, "usage", None)
            tokens_in = getattr(usage, "input_tokens", None) if usage else None
            tokens_out = getattr(usage, "output_tokens", None) if usage else None
            finish_reason = getattr(response, "status", None)
            response_id = getattr(response, "id", None)
            system_fingerprint = getattr(response, "system_fingerprint", None)
            return (
                parsed,
                finish_reason,
                tokens_in,
                tokens_out,
                response_id,
                system_fingerprint,
                response,
            )
        except (AttributeError, TypeError, OpenAIError):
            pass

        completion = await client.chat.completions.parse(
            model=self._model,
            messages=[
                {"role": "system", "content": system},
                {"role": "user", "content": user_content},
            ],
            response_format=output_type,
            temperature=temperature,
            max_completion_tokens=max_tokens,
        )
        choice = completion.choices[0] if completion.choices else None
        if choice is None:
            raise InvalidAIResponse("OpenAI returned no choices.")
        message = choice.message
        parsed = getattr(message, "parsed", None)
        refusal = getattr(message, "refusal", None)
        if refusal:
            raise InvalidAIResponse(f"OpenAI refused the request: {refusal}")
        finish_reason = choice.finish_reason
        usage = completion.usage
        tokens_in = getattr(usage, "prompt_tokens", None) if usage else None
        tokens_out = getattr(usage, "completion_tokens", None) if usage else None
        response_id = getattr(completion, "id", None)
        system_fingerprint = getattr(completion, "system_fingerprint", None)
        return (
            parsed,
            finish_reason,
            tokens_in,
            tokens_out,
            response_id,
            system_fingerprint,
            completion,
        )

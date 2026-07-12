"""Gemini LLM provider — Google Generative Language API (JSON mode)."""

from __future__ import annotations

import time
from datetime import UTC, datetime
from typing import Any, TypeVar

import httpx
from pydantic import BaseModel

from app.ai.exceptions import (
    AIConfigurationError,
    AIProviderError,
    InvalidAIResponse,
)
from app.ai.generation import GenerationRequest
from app.ai.gemini_settings import (
    DEFAULT_GEMINI_MODEL,
    GeminiSettings,
    get_gemini_settings,
)
from app.ai.models import ProviderHealth
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


class GeminiProvider(LLMProvider):
    """
    Google Gemini adapter.

    Uses ``generateContent`` with ``responseMimeType=application/json``.
    Grounding remains AIService-owned.
    """

    def __init__(
        self,
        *,
        model: str | None = None,
        api_key: str | None | object = _MISSING,
        base_url: str | None = None,
        timeout: float | None = None,
        settings: GeminiSettings | None = None,
        client: httpx.AsyncClient | None = None,
    ) -> None:
        cfg = settings or get_gemini_settings()
        self._api_key = cfg.api_key if api_key is _MISSING else api_key  # type: ignore[assignment]
        self._model = model or cfg.model or DEFAULT_GEMINI_MODEL
        self._base_url = (base_url or cfg.base_url).rstrip("/")
        self._timeout = float(timeout if timeout is not None else cfg.timeout)
        self._client = client
        self._capabilities = ProviderCapabilities(
            provider_name=AIProvider.GEMINI,
            supports_json=True,
            supports_streaming=True,
            supports_function_calling=True,
            supports_vision=True,
            supports_system_messages=True,
            supports_temperature=True,
            supports_seed=True,
            max_context_tokens=1_000_000,
            max_output_tokens=8_192,
            supports_response_schema=True,
            supports_tools=True,
            supports_images=True,
            supports_audio=True,
            supports_parallel_calls=False,
        )

    def name(self) -> AIProvider:
        return AIProvider.GEMINI

    def vendor(self) -> str:
        return "Google"

    def default_model(self) -> str:
        return DEFAULT_GEMINI_MODEL

    def api_version(self) -> str:
        return "v1beta"

    def model(self) -> str:
        return self._model

    @property
    def capabilities(self) -> ProviderCapabilities:
        return self._capabilities

    def is_available(self) -> bool:
        """Configured when an API key is present (used by feature routing)."""
        return bool(self._api_key)

    def _get_client(self) -> httpx.AsyncClient:
        if self._client is not None:
            return self._client
        if not self._api_key:
            raise AIConfigurationError(
                "GEMINI_API_KEY is not configured. Set it in the environment."
            )
        self._client = httpx.AsyncClient(timeout=self._timeout)
        return self._client

    async def health(self) -> ProviderHealth:
        return ProviderHealth(
            healthy=bool(self._api_key) or self._client is not None,
            provider=self.name(),
            model=self.model(),
            detail=(
                "API key configured"
                if (self._api_key or self._client is not None)
                else "GEMINI_API_KEY missing"
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
        feature = request.built_prompt.diagnostics.feature
        system = system_prompt_for(feature, request.options.system_prompt)
        user_content = request.rendered_text
        temperature = request.options.temperature
        max_tokens = request.options.max_output_tokens

        try:
            raw_text, finish_reason, tokens_in, tokens_out, response_id = (
                await self._call_gemini(
                    system=system,
                    user_content=user_content,
                    temperature=temperature,
                    max_tokens=max_tokens,
                )
            )
        except AIConfigurationError:
            raise
        except InvalidAIResponse:
            raise
        except httpx.TimeoutException as exc:
            raise AIProviderError(f"Gemini request timed out: {exc}") from exc
        except httpx.HTTPError as exc:
            raise AIProviderError(f"Gemini provider error: {exc}") from exc
        except Exception as exc:  # noqa: BLE001
            raise AIProviderError(f"Unexpected Gemini failure: {exc}") from exc

        provider_latency_ms = int((time.perf_counter() - started) * 1000)
        result = parse_structured_payload(
            parsed=raw_text,
            raw_payload=None,
            output_type=output_type,
            provider_label="Gemini",
        )

        total_tokens: int | None = None
        if tokens_in is not None or tokens_out is not None:
            total_tokens = (tokens_in or 0) + (tokens_out or 0)

        diagnostics = request.built_prompt.diagnostics.model_copy(
            update={
                "actual_tokens": (tokens_out if tokens_out is not None else None),
            }
        )
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
            system_fingerprint=None,
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

    async def _call_gemini(
        self,
        *,
        system: str,
        user_content: str,
        temperature: float | None,
        max_tokens: int | None,
    ) -> tuple[str, str | None, int | None, int | None, str | None]:
        client = self._get_client()
        url = f"{self._base_url}/models/{self._model}:generateContent"
        params = {"key": self._api_key}
        generation_config: dict[str, Any] = {
            "responseMimeType": "application/json",
        }
        if temperature is not None:
            generation_config["temperature"] = temperature
        if max_tokens is not None:
            generation_config["maxOutputTokens"] = max_tokens

        payload: dict[str, Any] = {
            "systemInstruction": {"parts": [{"text": system}]},
            "contents": [{"role": "user", "parts": [{"text": user_content}]}],
            "generationConfig": generation_config,
        }
        response = await client.post(url, params=params, json=payload)
        if response.status_code == 429:
            raise AIProviderError(
                f"Gemini rate limit (429): {response.text[:400]}"
            )
        if response.status_code >= 400:
            raise AIProviderError(
                f"Gemini provider error: HTTP {response.status_code}: "
                f"{response.text[:400]}"
            )
        body = response.json()
        candidates = body.get("candidates") or []
        if not candidates:
            raise InvalidAIResponse("Gemini returned no candidates.")
        candidate0 = candidates[0]
        finish_reason = candidate0.get("finishReason")
        parts = ((candidate0.get("content") or {}).get("parts")) or []
        texts = [
            part.get("text")
            for part in parts
            if isinstance(part, dict) and isinstance(part.get("text"), str)
        ]
        content = "".join(texts).strip()
        if not content:
            raise InvalidAIResponse("Gemini returned an empty structured payload.")
        usage = body.get("usageMetadata") or {}
        tokens_in = usage.get("promptTokenCount")
        tokens_out = usage.get("candidatesTokenCount")
        response_id = body.get("responseId")
        return (
            content,
            str(finish_reason) if finish_reason is not None else None,
            int(tokens_in) if isinstance(tokens_in, int) else None,
            int(tokens_out) if isinstance(tokens_out, int) else None,
            str(response_id) if response_id is not None else None,
        )

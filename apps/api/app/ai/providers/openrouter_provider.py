"""OpenRouter LLM provider — OpenAI-compatible API with shared structured parse."""

from __future__ import annotations

import logging
import time
from datetime import UTC, datetime
from typing import Any, NoReturn, TypeVar

from openai import APITimeoutError, AsyncOpenAI, OpenAIError, RateLimitError
from pydantic import BaseModel, ValidationError

from app.ai.constants import DEFAULT_OPENROUTER_MODEL
from app.ai.exceptions import (
    AIConfigurationError,
    AIProviderError,
    InvalidAIResponse,
)
from app.ai.generation import GenerationRequest
from app.ai.models import ProviderHealth
from app.ai.openrouter_settings import OpenRouterSettings, get_openrouter_settings
from app.ai.provider_capabilities import ProviderCapabilities
from app.ai.providers.base import LLMProvider
from app.ai.providers.openrouter_diagnostics import (
    build_provider_diagnostics,
    classify_content_type,
    recover_text_from_validation_error,
    status_code_from_exc,
    truncate_preview,
)
from app.ai.providers.provider_enum import AIProvider
from app.ai.providers.structured_output import (
    _coerce_json_text,
    parse_structured_payload,
    system_prompt_for,
)
from app.ai.response import AIResponse, ProviderResponseMetadata
from app.ai.telemetry import GenerationTelemetry

T = TypeVar("T")

_MISSING = object()
logger = logging.getLogger(__name__)

JSON_ONLY_RECOVERY_INSTRUCTION = (
    "You MUST return ONLY valid JSON.\n"
    "Do not include Markdown.\n"
    "Do not include LaTeX.\n"
    "Do not include explanations.\n"
    "Do not wrap the JSON in code fences.\n"
    "The first character of your response must be '{'."
)


class OpenRouterProvider(LLMProvider):
    """
    OpenRouter adapter (OpenAI-compatible HTTP).

    Uses the shared structured-output parser. Does not ground or validate
    business rules — AIService owns that.
    """

    def __init__(
        self,
        *,
        model: str | None = None,
        api_key: str | None | object = _MISSING,
        base_url: str | None = None,
        timeout: float | None = None,
        max_retries: int | None = None,
        settings: OpenRouterSettings | None = None,
        client: AsyncOpenAI | None = None,
    ) -> None:
        cfg = settings or get_openrouter_settings()
        self._api_key = cfg.api_key if api_key is _MISSING else api_key  # type: ignore[assignment]
        self._model = model or cfg.model or DEFAULT_OPENROUTER_MODEL
        self._base_url = (base_url or cfg.base_url).rstrip("/")
        self._timeout = float(timeout if timeout is not None else cfg.timeout)
        self._max_retries = int(
            max_retries if max_retries is not None else cfg.max_retries
        )
        self._http_referer = cfg.http_referer
        self._app_title = cfg.app_title
        self._client = client
        self._capabilities = ProviderCapabilities(
            provider_name=AIProvider.OPENROUTER,
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
        return AIProvider.OPENROUTER

    def vendor(self) -> str:
        return "OpenRouter"

    def default_model(self) -> str:
        return DEFAULT_OPENROUTER_MODEL

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

    def _default_headers(self) -> dict[str, str]:
        headers: dict[str, str] = {}
        if self._http_referer:
            headers["HTTP-Referer"] = self._http_referer
        if self._app_title:
            headers["X-Title"] = self._app_title
        return headers

    def _get_client(self) -> AsyncOpenAI:
        if self._client is not None:
            return self._client
        if not self._api_key:
            raise AIConfigurationError(
                "OPENROUTER_API_KEY is not configured. Set it in the environment."
            )
        self._client = AsyncOpenAI(
            api_key=self._api_key,
            base_url=self._base_url,
            timeout=self._timeout,
            max_retries=self._max_retries,
            default_headers=self._default_headers() or None,
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
                else "OPENROUTER_API_KEY missing"
            ),
        )

    def _diagnostics(
        self,
        *,
        stage: str | None,
        stage_latency_ms: dict[str, int],
        total_started: float,
        error_type: str | None = None,
        message: str | None = None,
        status_code: int | None = None,
        finish_reason: str | None = None,
        raw_preview: str | None = None,
        recovery_attempt: bool | None = None,
        recovery_reason: str | None = None,
        original_finish_reason: str | None = None,
        original_content_type: str | None = None,
    ) -> dict[str, Any]:
        return build_provider_diagnostics(
            provider=str(self.name()),
            model=self.model(),
            stage=stage,
            finish_reason=finish_reason,
            status_code=status_code,
            error_type=error_type,
            message=message,
            raw_preview=raw_preview,
            stage_latency_ms=stage_latency_ms,
            total_provider_ms=int((time.perf_counter() - total_started) * 1000),
            recovery_attempt=recovery_attempt,
            recovery_reason=recovery_reason,
            original_finish_reason=original_finish_reason,
            original_content_type=original_content_type,
        )

    def _raise_rate_limit(
        self,
        exc: RateLimitError,
        *,
        stage: str,
        stage_latency_ms: dict[str, int],
        total_started: float,
    ) -> NoReturn:
        diagnostics = self._diagnostics(
            stage=stage,
            stage_latency_ms=stage_latency_ms,
            total_started=total_started,
            error_type=type(exc).__name__,
            message=str(exc),
            status_code=status_code_from_exc(exc) or 429,
        )
        raise AIProviderError(
            f"OpenRouter rate limit (429): {exc}",
            diagnostics=diagnostics,
        ) from exc

    def _raise_timeout(
        self,
        exc: APITimeoutError,
        *,
        stage: str,
        stage_latency_ms: dict[str, int],
        total_started: float,
    ) -> NoReturn:
        diagnostics = self._diagnostics(
            stage=stage,
            stage_latency_ms=stage_latency_ms,
            total_started=total_started,
            error_type=type(exc).__name__,
            message=str(exc),
            status_code=status_code_from_exc(exc),
        )
        raise AIProviderError(
            f"OpenRouter request timed out: {exc}",
            diagnostics=diagnostics,
        ) from exc

    @staticmethod
    def _payload_text(
        parsed: BaseModel | dict[str, Any] | str | None,
        raw_payload: object,
    ) -> str | None:
        if isinstance(parsed, str) and parsed.strip():
            return parsed
        text = getattr(raw_payload, "output_text", None)
        if isinstance(text, str) and text.strip():
            return text
        choices = getattr(raw_payload, "choices", None)
        if choices:
            message = getattr(choices[0], "message", None)
            content = getattr(message, "content", None) if message else None
            if isinstance(content, str) and content.strip():
                return content
        return None

    @staticmethod
    def _is_invalid_json_error(exc: InvalidAIResponse) -> bool:
        message = (exc.message or str(exc)).lower()
        return "invalid json" in message or "empty structured payload" in message

    def _try_recover_validation_text(
        self,
        exc: ValidationError,
        *,
        stage: str,
        stage_latency_ms: dict[str, int],
        total_started: float,
    ) -> str | None:
        """
        Return SDK raw text when present.

        Valid JSON text is returned for immediate use. Non-JSON text returns
        ``None`` so the cascade can continue (json_object → recovery).
        """
        recovered = recover_text_from_validation_error(exc)
        if recovered and recovered.strip():
            try:
                _coerce_json_text(recovered)
            except Exception:  # noqa: BLE001 — non-JSON; continue cascade
                return None
            return recovered
        diagnostics = self._diagnostics(
            stage=stage,
            stage_latency_ms=stage_latency_ms,
            total_started=total_started,
            error_type=type(exc).__name__,
            message=str(exc),
            raw_preview=truncate_preview(str(exc)),
        )
        raise InvalidAIResponse(
            f"OpenRouter returned invalid JSON: {exc}",
            diagnostics=diagnostics,
        ) from exc

    async def _json_recovery_once(
        self,
        *,
        request: GenerationRequest[T],
        system: str,
        user_content: str,
        temperature: float | None,
        max_tokens: int | None,
        stage_latency_ms: dict[str, int],
        total_started: float,
        original_finish_reason: str | None,
        original_content_type: str,
        original_preview: str | None,
    ) -> tuple[
        str,
        str | None,
        int | None,
        int | None,
        str | None,
        str | None,
        object,
    ]:
        """One forced JSON-only chat.create — never retries again."""
        stage = "json_recovery"
        client = self._get_client()
        recovery_system = f"{system}\n\n{JSON_ONLY_RECOVERY_INSTRUCTION}"
        t0 = time.perf_counter()
        try:
            completion = await client.chat.completions.create(
                model=self._model,
                messages=[
                    {"role": "system", "content": recovery_system},
                    {"role": "user", "content": user_content},
                ],
                response_format={"type": "json_object"},
                temperature=temperature,
                max_tokens=max_tokens,
            )
        except RateLimitError as exc:
            stage_latency_ms[stage] = int((time.perf_counter() - t0) * 1000)
            diagnostics = self._diagnostics(
                stage=stage,
                stage_latency_ms=stage_latency_ms,
                total_started=total_started,
                error_type=type(exc).__name__,
                message=str(exc),
                status_code=status_code_from_exc(exc) or 429,
                recovery_attempt=True,
                recovery_reason="invalid_json",
                original_finish_reason=original_finish_reason,
                original_content_type=original_content_type,
                raw_preview=original_preview,
            )
            raise AIProviderError(
                f"OpenRouter rate limit (429): {exc}",
                diagnostics=diagnostics,
            ) from exc
        except APITimeoutError as exc:
            stage_latency_ms[stage] = int((time.perf_counter() - t0) * 1000)
            diagnostics = self._diagnostics(
                stage=stage,
                stage_latency_ms=stage_latency_ms,
                total_started=total_started,
                error_type=type(exc).__name__,
                message=str(exc),
                recovery_attempt=True,
                recovery_reason="invalid_json",
                original_finish_reason=original_finish_reason,
                original_content_type=original_content_type,
                raw_preview=original_preview,
            )
            raise AIProviderError(
                f"OpenRouter request timed out: {exc}",
                diagnostics=diagnostics,
            ) from exc
        except OpenAIError as exc:
            stage_latency_ms[stage] = int((time.perf_counter() - t0) * 1000)
            diagnostics = self._diagnostics(
                stage=stage,
                stage_latency_ms=stage_latency_ms,
                total_started=total_started,
                error_type=type(exc).__name__,
                message=str(exc),
                status_code=status_code_from_exc(exc),
                recovery_attempt=True,
                recovery_reason="invalid_json",
                original_finish_reason=original_finish_reason,
                original_content_type=original_content_type,
                raw_preview=original_preview,
            )
            raise AIProviderError(
                f"OpenRouter provider error: {exc}",
                diagnostics=diagnostics,
            ) from exc

        stage_latency_ms[stage] = int((time.perf_counter() - t0) * 1000)
        choice = completion.choices[0] if completion.choices else None
        if choice is None:
            raise InvalidAIResponse(
                "OpenRouter returned no choices.",
                diagnostics=self._diagnostics(
                    stage=stage,
                    stage_latency_ms=stage_latency_ms,
                    total_started=total_started,
                    error_type="NoChoices",
                    recovery_attempt=True,
                    recovery_reason="invalid_json",
                    original_finish_reason=original_finish_reason,
                    original_content_type=original_content_type,
                    raw_preview=original_preview,
                ),
            )
        content = getattr(choice.message, "content", None)
        if not (isinstance(content, str) and content.strip()):
            raise InvalidAIResponse(
                "OpenRouter returned an empty structured payload.",
                diagnostics=self._diagnostics(
                    stage=stage,
                    stage_latency_ms=stage_latency_ms,
                    total_started=total_started,
                    error_type="EmptyPayload",
                    finish_reason=choice.finish_reason,
                    recovery_attempt=True,
                    recovery_reason="invalid_json",
                    original_finish_reason=original_finish_reason,
                    original_content_type=original_content_type,
                    raw_preview=original_preview,
                ),
            )
        usage = completion.usage
        return (
            content,
            choice.finish_reason,
            getattr(usage, "prompt_tokens", None) if usage else None,
            getattr(usage, "completion_tokens", None) if usage else None,
            getattr(completion, "id", None),
            getattr(completion, "system_fingerprint", None),
            completion,
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
                stage_latency_ms,
            ) = await self._call_openrouter(
                request=request,
                output_type=output_type,
            )
        except AIProviderError:
            raise
        except InvalidAIResponse:
            raise
        except APITimeoutError as exc:
            raise AIProviderError(f"OpenRouter request timed out: {exc}") from exc
        except RateLimitError as exc:
            raise AIProviderError(f"OpenRouter rate limit (429): {exc}") from exc
        except OpenAIError as exc:
            raise AIProviderError(f"OpenRouter provider error: {exc}") from exc
        except AIConfigurationError:
            raise
        except Exception as exc:  # noqa: BLE001
            raise AIProviderError(f"Unexpected OpenRouter failure: {exc}") from exc

        provider_latency_ms = int((time.perf_counter() - started) * 1000)
        logger.info(
            "openrouter_provider_stages",
            extra={
                "model": self._model,
                "stage_latency_ms": stage_latency_ms,
                "total_provider_ms": provider_latency_ms,
            },
        )

        recovery_meta: dict[str, Any] | None = None
        try:
            result = parse_structured_payload(
                parsed=parsed,
                raw_payload=raw_payload,
                output_type=output_type,
                provider_label="OpenRouter",
            )
        except InvalidAIResponse as exc:
            if not self._is_invalid_json_error(exc):
                raise
            original_text = self._payload_text(parsed, raw_payload)
            content_type = classify_content_type(original_text)
            # Structured model instances that failed schema are not recovered here.
            if isinstance(parsed, BaseModel):
                raise
            # Do not attempt to parse LaTeX/markdown/prose — one JSON-only recovery.
            feature = request.built_prompt.diagnostics.feature
            system = system_prompt_for(feature, request.options.system_prompt)
            total_started = started
            try:
                (
                    parsed,
                    finish_reason,
                    tokens_in,
                    tokens_out,
                    response_id,
                    system_fingerprint,
                    raw_payload,
                ) = await self._json_recovery_once(
                    request=request,
                    system=system,
                    user_content=request.rendered_text,
                    temperature=request.options.temperature,
                    max_tokens=request.options.max_output_tokens,
                    stage_latency_ms=stage_latency_ms,
                    total_started=total_started,
                    original_finish_reason=finish_reason,
                    original_content_type=content_type,
                    original_preview=truncate_preview(original_text),
                )
            except (AIProviderError, InvalidAIResponse) as recovery_exc:
                # Preserve recovery diagnostics on the raised error when present.
                if getattr(recovery_exc, "diagnostics", None) is None:
                    recovery_exc.diagnostics = self._diagnostics(  # type: ignore[attr-defined]
                        stage="json_recovery",
                        stage_latency_ms=stage_latency_ms,
                        total_started=total_started,
                        error_type=type(recovery_exc).__name__,
                        message=str(recovery_exc),
                        recovery_attempt=True,
                        recovery_reason="invalid_json",
                        original_finish_reason=finish_reason,
                        original_content_type=content_type,
                        raw_preview=truncate_preview(original_text),
                    )
                raise
            recovery_meta = {
                "recovery_attempt": True,
                "recovery_reason": "invalid_json",
                "original_finish_reason": finish_reason,
                "original_content_type": content_type,
            }
            logger.info(
                "openrouter_json_recovery",
                extra={
                    "model": self._model,
                    "original_content_type": content_type,
                    "stage_latency_ms": stage_latency_ms,
                },
            )
            try:
                result = parse_structured_payload(
                    parsed=parsed,
                    raw_payload=raw_payload,
                    output_type=output_type,
                    provider_label="OpenRouter",
                )
            except InvalidAIResponse as recovery_parse_exc:
                raise InvalidAIResponse(
                    recovery_parse_exc.message,
                    diagnostics=self._diagnostics(
                        stage="json_recovery",
                        stage_latency_ms=stage_latency_ms,
                        total_started=total_started,
                        error_type=type(recovery_parse_exc).__name__,
                        message=str(recovery_parse_exc),
                        recovery_attempt=True,
                        recovery_reason="invalid_json",
                        original_finish_reason=finish_reason,
                        original_content_type=content_type,
                        raw_preview=truncate_preview(
                            self._payload_text(parsed, raw_payload) or original_text
                        ),
                    ),
                ) from recovery_parse_exc

        provider_latency_ms = int((time.perf_counter() - started) * 1000)

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
            retry_count=1 if recovery_meta else 0,
            generation_status="success",
            request_id=None,
            response_id=response_id,
            system_fingerprint=system_fingerprint,
        )
        # Map stage timings onto existing telemetry slots (no DTO changes).
        responses_ms = stage_latency_ms.get("responses.parse")
        chat_parse_ms = stage_latency_ms.get("chat.parse")
        json_object_ms = stage_latency_ms.get("json_object")
        recovery_ms = stage_latency_ms.get("json_recovery")
        parse_stage_ms = (
            recovery_ms
            if recovery_ms is not None
            else (chat_parse_ms if chat_parse_ms is not None else json_object_ms)
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
            prompt_build_latency_ms=responses_ms,
            response_parse_latency_ms=parse_stage_ms,
            tokens_in=tokens_in,
            tokens_out=tokens_out,
            cost_usd=None,
            status="success",
            generation_status="success",
            finish_reason=finish_reason,
            retry_count=1 if recovery_meta else 0,
            request_id=None,
            created_at=generated_at,
            error=(
                f"recovered_from={recovery_meta.get('original_content_type')}"
                if recovery_meta
                else None
            ),
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

    async def _call_openrouter(
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
        dict[str, int],
    ]:
        client = self._get_client()
        user_content = request.rendered_text
        temperature = request.options.temperature
        max_tokens = request.options.max_output_tokens
        feature = request.built_prompt.diagnostics.feature
        system = system_prompt_for(feature, request.options.system_prompt)

        stage_latency_ms: dict[str, int] = {}
        total_started = time.perf_counter()

        # Prefer Responses API structured parse when available.
        stage = "responses.parse"
        t0 = time.perf_counter()
        try:
            response = await client.responses.parse(
                model=self._model,
                instructions=system,
                input=user_content,
                text_format=output_type,
                temperature=temperature,
                max_output_tokens=max_tokens,
            )
            stage_latency_ms[stage] = int((time.perf_counter() - t0) * 1000)
            parsed = getattr(response, "output_parsed", None)
            output_text = getattr(response, "output_text", None)
            if parsed is not None:
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
                    stage_latency_ms,
                )
            if isinstance(output_text, str) and output_text.strip():
                try:
                    _coerce_json_text(output_text)
                except Exception:  # noqa: BLE001 — non-JSON; continue cascade
                    pass
                else:
                    usage = getattr(response, "usage", None)
                    tokens_in = getattr(usage, "input_tokens", None) if usage else None
                    tokens_out = (
                        getattr(usage, "output_tokens", None) if usage else None
                    )
                    finish_reason = getattr(response, "status", None)
                    response_id = getattr(response, "id", None)
                    system_fingerprint = getattr(
                        response, "system_fingerprint", None
                    )
                    return (
                        output_text,
                        finish_reason,
                        tokens_in,
                        tokens_out,
                        response_id,
                        system_fingerprint,
                        response,
                        stage_latency_ms,
                    )
            # Empty / non-JSON Responses payload — fall through to chat completions.
        except RateLimitError as exc:
            stage_latency_ms[stage] = int((time.perf_counter() - t0) * 1000)
            self._raise_rate_limit(
                exc,
                stage=stage,
                stage_latency_ms=stage_latency_ms,
                total_started=total_started,
            )
        except APITimeoutError as exc:
            stage_latency_ms[stage] = int((time.perf_counter() - t0) * 1000)
            self._raise_timeout(
                exc,
                stage=stage,
                stage_latency_ms=stage_latency_ms,
                total_started=total_started,
            )
        except ValidationError as exc:
            stage_latency_ms[stage] = int((time.perf_counter() - t0) * 1000)
            recovered = self._try_recover_validation_text(
                exc,
                stage=stage,
                stage_latency_ms=stage_latency_ms,
                total_started=total_started,
            )
            if recovered is not None:
                return (
                    recovered,
                    None,
                    None,
                    None,
                    None,
                    None,
                    None,
                    stage_latency_ms,
                )
            # Non-JSON ValidationError payload — continue cascade.
        except (AttributeError, TypeError):
            stage_latency_ms[stage] = int((time.perf_counter() - t0) * 1000)
        except OpenAIError:
            # Unsupported / unavailable Responses path — try chat completions.
            stage_latency_ms[stage] = int((time.perf_counter() - t0) * 1000)

        # Chat Completions structured parse.
        stage = "chat.parse"
        t0 = time.perf_counter()
        try:
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
            stage_latency_ms[stage] = int((time.perf_counter() - t0) * 1000)
            choice = completion.choices[0] if completion.choices else None
            if choice is None:
                raise InvalidAIResponse(
                    "OpenRouter returned no choices.",
                    diagnostics=self._diagnostics(
                        stage=stage,
                        stage_latency_ms=stage_latency_ms,
                        total_started=total_started,
                        error_type="NoChoices",
                    ),
                )
            message = choice.message
            parsed = getattr(message, "parsed", None)
            refusal = getattr(message, "refusal", None)
            if refusal:
                raise InvalidAIResponse(
                    f"OpenRouter refused the request: {refusal}",
                    diagnostics=self._diagnostics(
                        stage=stage,
                        stage_latency_ms=stage_latency_ms,
                        total_started=total_started,
                        error_type="Refusal",
                        message=str(refusal),
                        finish_reason=choice.finish_reason,
                    ),
                )
            content = getattr(message, "content", None)
            # Prefer structured parse; non-JSON free-model text falls through.
            if parsed is not None:
                finish_reason = choice.finish_reason
                usage = completion.usage
                tokens_in = getattr(usage, "prompt_tokens", None) if usage else None
                tokens_out = (
                    getattr(usage, "completion_tokens", None) if usage else None
                )
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
                    stage_latency_ms,
                )
            if isinstance(content, str) and content.strip():
                try:
                    _coerce_json_text(content)
                except Exception:  # noqa: BLE001 — non-JSON; try json_object
                    pass
                else:
                    finish_reason = choice.finish_reason
                    usage = completion.usage
                    tokens_in = (
                        getattr(usage, "prompt_tokens", None) if usage else None
                    )
                    tokens_out = (
                        getattr(usage, "completion_tokens", None) if usage else None
                    )
                    response_id = getattr(completion, "id", None)
                    system_fingerprint = getattr(
                        completion, "system_fingerprint", None
                    )
                    return (
                        content,
                        finish_reason,
                        tokens_in,
                        tokens_out,
                        response_id,
                        system_fingerprint,
                        completion,
                        stage_latency_ms,
                    )
            # Empty / non-JSON chat.parse — fall through to json_object.
        except InvalidAIResponse:
            raise
        except RateLimitError as exc:
            stage_latency_ms[stage] = int((time.perf_counter() - t0) * 1000)
            self._raise_rate_limit(
                exc,
                stage=stage,
                stage_latency_ms=stage_latency_ms,
                total_started=total_started,
            )
        except APITimeoutError as exc:
            stage_latency_ms[stage] = int((time.perf_counter() - t0) * 1000)
            self._raise_timeout(
                exc,
                stage=stage,
                stage_latency_ms=stage_latency_ms,
                total_started=total_started,
            )
        except ValidationError as exc:
            stage_latency_ms[stage] = int((time.perf_counter() - t0) * 1000)
            recovered = self._try_recover_validation_text(
                exc,
                stage=stage,
                stage_latency_ms=stage_latency_ms,
                total_started=total_started,
            )
            if recovered is not None:
                # Reuse shared coercion / schema validation in parse_structured_payload.
                return (
                    recovered,
                    None,
                    None,
                    None,
                    None,
                    None,
                    None,
                    stage_latency_ms,
                )
            # Non-JSON ValidationError payload — try json_object next.
        except (AttributeError, TypeError):
            stage_latency_ms[stage] = int((time.perf_counter() - t0) * 1000)
        except OpenAIError:
            # Generic upstream / unsupported schema parse — try json_object.
            stage_latency_ms[stage] = int((time.perf_counter() - t0) * 1000)

        # JSON-mode chat create — works with most OpenRouter free models.
        stage = "json_object"
        t0 = time.perf_counter()
        try:
            completion = await client.chat.completions.create(
                model=self._model,
                messages=[
                    {"role": "system", "content": system},
                    {"role": "user", "content": user_content},
                ],
                response_format={"type": "json_object"},
                temperature=temperature,
                max_tokens=max_tokens,
            )
        except RateLimitError as exc:
            stage_latency_ms[stage] = int((time.perf_counter() - t0) * 1000)
            self._raise_rate_limit(
                exc,
                stage=stage,
                stage_latency_ms=stage_latency_ms,
                total_started=total_started,
            )
        except APITimeoutError as exc:
            stage_latency_ms[stage] = int((time.perf_counter() - t0) * 1000)
            self._raise_timeout(
                exc,
                stage=stage,
                stage_latency_ms=stage_latency_ms,
                total_started=total_started,
            )
        except OpenAIError as exc:
            stage_latency_ms[stage] = int((time.perf_counter() - t0) * 1000)
            diagnostics = self._diagnostics(
                stage=stage,
                stage_latency_ms=stage_latency_ms,
                total_started=total_started,
                error_type=type(exc).__name__,
                message=str(exc),
                status_code=status_code_from_exc(exc),
            )
            raise AIProviderError(
                f"OpenRouter provider error: {exc}",
                diagnostics=diagnostics,
            ) from exc

        stage_latency_ms[stage] = int((time.perf_counter() - t0) * 1000)
        choice = completion.choices[0] if completion.choices else None
        if choice is None:
            raise InvalidAIResponse(
                "OpenRouter returned no choices.",
                diagnostics=self._diagnostics(
                    stage=stage,
                    stage_latency_ms=stage_latency_ms,
                    total_started=total_started,
                    error_type="NoChoices",
                ),
            )
        content = getattr(choice.message, "content", None)
        finish_reason = choice.finish_reason
        usage = completion.usage
        tokens_in = getattr(usage, "prompt_tokens", None) if usage else None
        tokens_out = getattr(usage, "completion_tokens", None) if usage else None
        response_id = getattr(completion, "id", None)
        system_fingerprint = getattr(completion, "system_fingerprint", None)
        # Return even non-JSON / empty text — generate() may run one JSON recovery.
        return (
            content if isinstance(content, str) else None,
            finish_reason,
            tokens_in,
            tokens_out,
            response_id,
            system_fingerprint,
            completion,
            stage_latency_ms,
        )

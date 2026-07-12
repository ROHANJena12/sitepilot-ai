"""Anthropic provider placeholder (no SDK / no HTTP)."""

from __future__ import annotations

from typing import TypeVar

from app.ai.generation import GenerationRequest
from app.ai.models import ProviderHealth
from app.ai.provider_capabilities import ProviderCapabilities
from app.ai.providers.base import LLMProvider
from app.ai.providers.provider_enum import AIProvider
from app.ai.response import AIResponse

T = TypeVar("T")


class AnthropicProvider(LLMProvider):
    """Contract stub for Anthropic. Generation not implemented yet."""

    def __init__(self, *, model: str = "claude-3-5-sonnet-latest") -> None:
        self._model = model
        self._capabilities = ProviderCapabilities(
            provider_name=AIProvider.ANTHROPIC,
            supports_json=True,
            supports_streaming=True,
            supports_function_calling=True,
            supports_vision=True,
            supports_system_messages=True,
            supports_temperature=True,
            supports_seed=False,
            max_context_tokens=200_000,
            max_output_tokens=8_192,
            supports_response_schema=False,
            supports_tools=True,
            supports_images=True,
            supports_audio=False,
            supports_parallel_calls=False,
        )

    def name(self) -> AIProvider:
        return AIProvider.ANTHROPIC

    def vendor(self) -> str:
        return "Anthropic"

    def default_model(self) -> str:
        return "claude-3-5-sonnet-latest"

    def api_version(self) -> str:
        return "2023-06-01"

    def model(self) -> str:
        return self._model

    @property
    def capabilities(self) -> ProviderCapabilities:
        return self._capabilities

    async def health(self) -> ProviderHealth:
        return ProviderHealth(
            healthy=False,
            provider=self.name(),
            model=self.model(),
            detail="Placeholder — remote health check not implemented",
        )

    async def generate(self, request: GenerationRequest[T]) -> AIResponse[T]:
        raise NotImplementedError(
            "AnthropicProvider.generate is not implemented "
            "(AI foundation only — no LLM calls)."
        )

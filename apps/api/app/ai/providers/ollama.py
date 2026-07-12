"""Ollama provider placeholder (no SDK / no HTTP)."""

from __future__ import annotations

from typing import TypeVar

from app.ai.generation import GenerationRequest
from app.ai.models import ProviderHealth
from app.ai.provider_capabilities import ProviderCapabilities
from app.ai.providers.base import LLMProvider
from app.ai.providers.provider_enum import AIProvider
from app.ai.response import AIResponse

T = TypeVar("T")


class OllamaProvider(LLMProvider):
    """Contract stub for local Ollama. Generation not implemented yet."""

    def __init__(self, *, model: str = "llama3.1") -> None:
        self._model = model
        self._capabilities = ProviderCapabilities(
            provider_name=AIProvider.OLLAMA,
            supports_json=True,
            supports_streaming=True,
            supports_function_calling=False,
            supports_vision=False,
            supports_system_messages=True,
            supports_temperature=True,
            supports_seed=True,
            max_context_tokens=32_768,
            max_output_tokens=4_096,
            supports_response_schema=False,
            supports_tools=False,
            supports_images=False,
            supports_audio=False,
            supports_parallel_calls=False,
        )

    def name(self) -> AIProvider:
        return AIProvider.OLLAMA

    def vendor(self) -> str:
        return "Ollama"

    def default_model(self) -> str:
        return "llama3.1"

    def api_version(self) -> str:
        return "local"

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
            "OllamaProvider.generate is not implemented "
            "(AI foundation only — no LLM calls)."
        )

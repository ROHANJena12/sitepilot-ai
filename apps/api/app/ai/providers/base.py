"""LLM provider contract with static metadata + capabilities."""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import TypeVar

from app.ai.generation import GenerationRequest
from app.ai.models import ProviderHealth
from app.ai.provider_capabilities import ProviderCapabilities
from app.ai.providers.provider_enum import AIProvider
from app.ai.response import AIResponse

T = TypeVar("T")


class LLMProvider(ABC):
    """
    Provider-agnostic LLM interface.

    Implementations advertise capabilities via ``capabilities``.
    OpenAI implements ``generate`` for FindingExplanation (Sprint 18).
    Other providers remain placeholders until wired.
    """

    @abstractmethod
    def name(self) -> AIProvider:
        """Canonical provider id (``AIProvider``; JSON/env still use string values)."""

    @abstractmethod
    def vendor(self) -> str:
        """Vendor / organization name."""

    @abstractmethod
    def default_model(self) -> str:
        """Vendor default model id (may differ from instance ``model()``)."""

    @abstractmethod
    def api_version(self) -> str:
        """Static API version label (no HTTP)."""

    @abstractmethod
    def model(self) -> str:
        """Configured model id for this instance."""

    @property
    @abstractmethod
    def capabilities(self) -> ProviderCapabilities:
        """Immutable capability advertisement for this provider."""

    @abstractmethod
    async def health(self) -> ProviderHealth:
        """
        Lightweight readiness probe.

        Architecture sprints: return a static result — do not call remote APIs.
        """

    @abstractmethod
    async def generate(self, request: GenerationRequest[T]) -> AIResponse[T]:
        """
        Generate a typed completion from ``GenerationRequest[T]``.

        Returns parsed schema output + provider metadata.
        Grounding is applied by AIService, not by providers.
        """

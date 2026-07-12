"""SitePilot AI foundation — provider-agnostic LLM infrastructure.

Sprint 18+: OpenAI explanations with reusable grounding validators.
Provider metadata is separate from business results
(``AIResponse.provider_metadata``). Platform quality lives in
``AIResponse.quality`` (``AIQualityMetadata``) — never LLM-authored.
"""

from __future__ import annotations

from app.ai.cache import AICache, InMemoryAICache, NullAICache, build_cache_key
from app.ai.config import AISettings, clear_ai_settings_cache, get_ai_settings
from app.ai.context import AIContext
from app.ai.diagnostics import PromptDiagnostics
from app.ai.features import AIFeature, GenerationId, resolve_feature, prompt_id_for
from app.ai.factory import ProviderFactory
from app.ai.generation import GenerationOptions, GenerationRequest
from app.ai.provider_capabilities import ProviderCapabilities
from app.ai.providers.provider_enum import AIProvider, provider_name, resolve_provider
from app.ai.registry import ProviderRegistry, get_provider_registry
from app.ai.response import AIQualityMetadata, AIResponse, ProviderResponseMetadata
from app.ai.service import AIService
from app.ai.session import GenerationSession
from app.ai.telemetry import GenerationTelemetry

__all__ = [
    "AICache",
    "AIContext",
    "AIFeature",
    "AIProvider",
    "AIQualityMetadata",
    "AIResponse",
    "AIService",
    "AISettings",
    "GenerationId",
    "GenerationOptions",
    "GenerationRequest",
    "GenerationSession",
    "GenerationTelemetry",
    "InMemoryAICache",
    "NullAICache",
    "PromptDiagnostics",
    "ProviderCapabilities",
    "ProviderFactory",
    "ProviderRegistry",
    "ProviderResponseMetadata",
    "build_cache_key",
    "clear_ai_settings_cache",
    "get_ai_settings",
    "get_provider_registry",
    "prompt_id_for",
    "provider_name",
    "resolve_feature",
    "resolve_provider",
]

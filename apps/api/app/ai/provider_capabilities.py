"""Immutable provider capability advertisements."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field

from app.ai.providers.provider_enum import AIProvider


class ProviderCapabilities(BaseModel):
    """
    Static capability matrix for an LLM provider.

    AIService must consult this object — never hardcode provider behavior.
    """

    model_config = ConfigDict(frozen=True, extra="forbid")

    provider_name: AIProvider
    supports_json: bool = False
    supports_streaming: bool = False
    supports_function_calling: bool = False
    supports_vision: bool = False
    supports_system_messages: bool = False
    supports_temperature: bool = True
    supports_seed: bool = False
    max_context_tokens: int | None = Field(default=None, ge=1)
    max_output_tokens: int | None = Field(default=None, ge=1)
    supports_response_schema: bool = False
    supports_tools: bool = False
    supports_images: bool = False
    supports_audio: bool = False
    supports_parallel_calls: bool = False

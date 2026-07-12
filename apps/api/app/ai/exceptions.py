"""Typed exceptions for the AI foundation layer."""

from __future__ import annotations

from typing import Any


class AIError(Exception):
    """Base AI foundation error."""

    code: str = "AI_ERROR"

    def __init__(
        self,
        message: str,
        *,
        code: str | None = None,
        diagnostics: dict[str, Any] | None = None,
    ) -> None:
        self.message = message
        self.diagnostics = diagnostics
        if code is not None:
            self.code = code
        super().__init__(message)


class ProviderNotFound(AIError):
    code = "PROVIDER_NOT_FOUND"


class PromptNotFound(AIError):
    code = "PROMPT_NOT_FOUND"


class PromptValidationError(AIError):
    code = "PROMPT_VALIDATION_ERROR"


class AIConfigurationError(AIError):
    code = "AI_CONFIGURATION_ERROR"


class CacheError(AIError):
    code = "CACHE_ERROR"


class GenerationNotImplemented(AIError):
    """Raised when a generation feature is not wired for the active sprint."""

    code = "GENERATION_NOT_IMPLEMENTED"


class BuilderNotFound(AIError):
    code = "BUILDER_NOT_FOUND"


class CapabilityNotSupported(AIError):
    """Provider capabilities cannot satisfy GenerationOptions."""

    code = "CAPABILITY_NOT_SUPPORTED"


class ServiceNotReady(AIError):
    """AIService readiness preflight failed."""

    code = "SERVICE_NOT_READY"


class InvalidAIResponse(AIError):
    """Model output failed JSON / schema / grounding validation."""

    code = "INVALID_AI_RESPONSE"


class AIProviderError(AIError):
    """Upstream provider failure (timeout, API error, etc.)."""

    code = "AI_PROVIDER_ERROR"

"""GroundingValidator contract — pure validation, never calls providers."""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Generic, TypeVar

from app.ai.context import AIContext

T = TypeVar("T")


class GroundingValidator(ABC, Generic[T]):
    """
    Closed-world validator for a structured AI output type.

    Implementations must be pure Python: no OpenAI/SDK/HTTP/DB calls.
    Raise ``InvalidAIResponse`` when grounding fails.
    """

    @abstractmethod
    def validate(self, output: T, context: AIContext) -> T:
        """Return ``output`` if grounded; otherwise raise ``InvalidAIResponse``."""

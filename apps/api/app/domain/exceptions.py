"""Domain exceptions for invariant violations (not HTTP layer)."""

from __future__ import annotations


class DomainValidationError(ValueError):
    """Raised when a domain invariant or value object validation fails."""

    def __init__(self, message: str, *, code: str = "DOMAIN_VALIDATION") -> None:
        super().__init__(message)
        self.code = code
        self.message = message

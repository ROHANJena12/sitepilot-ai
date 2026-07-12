"""Business Intelligence Engine exceptions."""

from __future__ import annotations


class BusinessError(Exception):
    """Base class for business engine failures."""

    def __init__(self, message: str, *, code: str) -> None:
        super().__init__(message)
        self.message = message
        self.code = code


class MissingAnalysisError(BusinessError):
    """One or more upstream analyses are missing from shared state."""

    def __init__(
        self,
        message: str = "Upstream analysis outputs are required in shared_state.",
        *,
        code: str = "MISSING_ANALYSIS",
        missing: tuple[str, ...] = (),
    ) -> None:
        super().__init__(message, code=code)
        self.missing = missing


class InvalidAnalysisError(BusinessError):
    """Upstream shared_state value is not a recognized analysis object."""

    def __init__(
        self,
        message: str = "Upstream analysis must expose a findings collection.",
        *,
        code: str = "INVALID_ANALYSIS",
    ) -> None:
        super().__init__(message, code=code)

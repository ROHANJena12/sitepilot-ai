"""Security Intelligence Engine exceptions."""

from __future__ import annotations


class SecurityError(Exception):
    """Base class for security engine failures."""

    def __init__(self, message: str, *, code: str) -> None:
        super().__init__(message)
        self.message = message
        self.code = code


class MissingDocumentError(SecurityError):
    """Document is not present in AuditContext shared state."""

    def __init__(
        self,
        message: str = "Document is required in shared_state['document'].",
        *,
        code: str = "MISSING_DOCUMENT",
    ) -> None:
        super().__init__(message, code=code)


class InvalidDocumentError(SecurityError):
    """shared_state['document'] is not a Document instance."""

    def __init__(
        self,
        message: str = "shared_state['document'] must be a Document instance.",
        *,
        code: str = "INVALID_DOCUMENT",
    ) -> None:
        super().__init__(message, code=code)


class MissingCrawlMetadataError(SecurityError):
    """Crawler headers / final URL are missing from shared state."""

    def __init__(
        self,
        message: str = "Crawler metadata (headers/final_url) is required.",
        *,
        code: str = "MISSING_CRAWL_METADATA",
    ) -> None:
        super().__init__(message, code=code)

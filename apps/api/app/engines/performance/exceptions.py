"""Performance Intelligence Engine exceptions."""

from __future__ import annotations


class PerformanceError(Exception):
    """Base class for performance engine failures."""

    def __init__(self, message: str, *, code: str) -> None:
        super().__init__(message)
        self.message = message
        self.code = code


class MissingDocumentError(PerformanceError):
    def __init__(
        self,
        message: str = "Document is required in shared_state['document'].",
        *,
        code: str = "MISSING_DOCUMENT",
    ) -> None:
        super().__init__(message, code=code)


class InvalidDocumentError(PerformanceError):
    def __init__(
        self,
        message: str = "shared_state['document'] must be a Document instance.",
        *,
        code: str = "INVALID_DOCUMENT",
    ) -> None:
        super().__init__(message, code=code)


class MissingCrawlMetadataError(PerformanceError):
    def __init__(
        self,
        message: str = "Crawler metadata (headers/final_url) is required.",
        *,
        code: str = "MISSING_CRAWL_METADATA",
    ) -> None:
        super().__init__(message, code=code)

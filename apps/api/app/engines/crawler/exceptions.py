"""Structured exceptions for the Crawler Engine."""

from __future__ import annotations


class CrawlerError(Exception):
    """Base class for crawler failures."""

    def __init__(self, message: str, *, code: str) -> None:
        super().__init__(message)
        self.message = message
        self.code = code


class NetworkTimeoutError(CrawlerError):
    """Connect / read / total request timed out."""

    def __init__(self, message: str = "Crawl request timed out.", *, code: str = "CRAWL_TIMEOUT") -> None:
        super().__init__(message, code=code)


class TooManyRedirectsError(CrawlerError):
    """Redirect chain exceeded the configured maximum."""

    def __init__(
        self,
        message: str = "Too many redirects.",
        *,
        code: str = "TOO_MANY_REDIRECTS",
    ) -> None:
        super().__init__(message, code=code)


class RedirectLoopError(CrawlerError):
    """A URL repeated in the redirect chain."""

    def __init__(
        self,
        message: str = "Redirect loop detected.",
        *,
        code: str = "REDIRECT_LOOP",
    ) -> None:
        super().__init__(message, code=code)


class InvalidContentTypeError(CrawlerError):
    """Response Content-Type is not an allowed HTML document type."""

    def __init__(
        self,
        message: str = "Unsupported content type for crawl.",
        *,
        code: str = "UNSUPPORTED_CONTENT_TYPE",
    ) -> None:
        super().__init__(message, code=code)


class DownloadTooLargeError(CrawlerError):
    """Response body exceeded the maximum download size."""

    def __init__(
        self,
        message: str = "Response body exceeds maximum allowed size.",
        *,
        code: str = "RESPONSE_TOO_LARGE",
    ) -> None:
        super().__init__(message, code=code)


class SslError(CrawlerError):
    """TLS handshake or certificate verification failed."""

    def __init__(self, message: str = "TLS/SSL error during crawl.", *, code: str = "TLS_ERROR") -> None:
        super().__init__(message, code=code)


class ConnectionError(CrawlerError):
    """TCP / HTTP connection failure."""

    def __init__(
        self,
        message: str = "Failed to connect to origin.",
        *,
        code: str = "CONNECTION_ERROR",
    ) -> None:
        super().__init__(message, code=code)


# Back-compat alias used in early drafts.
CrawlerConnectionError = ConnectionError


class HttpStatusError(CrawlerError):
    """Optional hard-fail for unexpected HTTP status (rarely raised; status is usually recorded)."""

    def __init__(
        self,
        message: str,
        *,
        status_code: int,
        code: str = "HTTP_STATUS_ERROR",
    ) -> None:
        super().__init__(message, code=code)
        self.status_code = status_code


class InvalidRedirectError(CrawlerError):
    """Redirect response missing or invalid Location."""

    def __init__(
        self,
        message: str = "Invalid or missing redirect Location.",
        *,
        code: str = "INVALID_REDIRECT",
    ) -> None:
        super().__init__(message, code=code)


class SsrfBlockedError(CrawlerError):
    """Redirect or request target failed SSRF checks."""

    def __init__(
        self,
        message: str = "Crawl target is not a public internet address.",
        *,
        code: str = "SSRF_BLOCKED",
    ) -> None:
        super().__init__(message, code=code)


class EmptyBodyError(CrawlerError):
    """Final response body was empty."""

    def __init__(self, message: str = "Response body is empty.", *, code: str = "EMPTY_BODY") -> None:
        super().__init__(message, code=code)


class MissingUrlError(CrawlerError):
    """No normalized/requested URL available in context."""

    def __init__(
        self,
        message: str = "No URL available for crawl.",
        *,
        code: str = "URL_REQUIRED",
    ) -> None:
        super().__init__(message, code=code)

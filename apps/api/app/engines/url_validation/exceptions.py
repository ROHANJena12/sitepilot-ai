"""Structured exceptions for URL Validation Engine failures.

These are raised by lower-level helpers. ``validate_url`` maps them into
``ValidationResult.validation_errors`` so the engine API stays result-oriented.
"""

from __future__ import annotations


class UrlValidationError(Exception):
    """Base class for URL validation failures."""

    def __init__(self, message: str, *, code: str) -> None:
        super().__init__(message)
        self.message = message
        self.code = code


class MalformedUrlError(UrlValidationError):
    """URL syntax is invalid or incomplete."""

    def __init__(self, message: str = "URL is malformed or incomplete.", *, code: str = "INVALID_URL") -> None:
        super().__init__(message, code=code)


class InvalidSchemeError(UrlValidationError):
    """Scheme is missing after normalization or not http/https."""

    def __init__(self, message: str = "URL scheme must be http or https.", *, code: str = "INVALID_SCHEME") -> None:
        super().__init__(message, code=code)


class UnsupportedProtocolError(UrlValidationError):
    """Explicitly blocked protocol (file, ftp, javascript, data, …)."""

    def __init__(
        self,
        message: str = "URL protocol is not supported.",
        *,
        code: str = "INVALID_SCHEME",
    ) -> None:
        super().__init__(message, code=code)


class PrivateAddressError(UrlValidationError):
    """Hostname or resolved IP is not a public internet target (SSRF)."""

    def __init__(
        self,
        message: str = "Resolved address is not a public internet target.",
        *,
        code: str = "SSRF_BLOCKED",
    ) -> None:
        super().__init__(message, code=code)


class DnsResolutionError(UrlValidationError):
    """Hostname could not be resolved via DNS."""

    def __init__(
        self,
        message: str = "DNS resolution failed for hostname.",
        *,
        code: str = "DNS_FAILURE",
    ) -> None:
        super().__init__(message, code=code)

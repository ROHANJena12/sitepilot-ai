"""Content-type, size, and SSRF validation for crawl targets."""

from __future__ import annotations

import ipaddress
from urllib.parse import urljoin, urlparse

from app.engines.crawler.constants import (
    ALLOWED_HTML_CONTENT_TYPES,
    REJECTED_CONTENT_TYPE_PREFIXES,
)
from app.engines.crawler.exceptions import (
    DownloadTooLargeError,
    InvalidContentTypeError,
    InvalidRedirectError,
    SsrfBlockedError,
)
from app.engines.url_validation.validators import is_blocked_hostname, is_public_ip


def normalize_content_type(header_value: str | None) -> str | None:
    """Return the media type portion of a Content-Type header (lowercased)."""
    if not header_value:
        return None
    return header_value.split(";", 1)[0].strip().lower() or None


def extract_charset(header_value: str | None) -> str | None:
    """Extract charset from Content-Type if present."""
    if not header_value:
        return None
    parts = [p.strip() for p in header_value.split(";")]
    for part in parts[1:]:
        if part.lower().startswith("charset="):
            return part.split("=", 1)[1].strip().strip('"').lower() or None
    return None


def looks_like_html(body_prefix: bytes | str) -> bool:
    """Best-effort HTML sniff for missing/ambiguous Content-Type."""
    if isinstance(body_prefix, bytes):
        sample = body_prefix[:512].decode("utf-8", errors="ignore").lower()
    else:
        sample = body_prefix[:512].lower()
    stripped = sample.lstrip()
    return stripped.startswith("<!doctype html") or stripped.startswith("<html") or "<html" in stripped[:200]


def assert_allowed_content_type(
    content_type_header: str | None,
    *,
    body_prefix: bytes | str = b"",
) -> str:
    """
    Validate Content-Type is HTML (or sniffable as HTML).

    Rules:
    - Reject known binary prefixes (image/, pdf, zip, audio/, video/, …).
    - Allow ``text/html`` and ``application/xhtml+xml``.
    - If Content-Type missing/unknown, allow only when body sniffs as HTML.
    """
    media = normalize_content_type(content_type_header)
    if media is not None:
        for prefix in REJECTED_CONTENT_TYPE_PREFIXES:
            if media.startswith(prefix) or media == prefix.rstrip("/"):
                raise InvalidContentTypeError(
                    f"Content-Type '{media}' is not allowed for crawling.",
                )
        if media in ALLOWED_HTML_CONTENT_TYPES:
            return media
        if media.startswith("text/") and looks_like_html(body_prefix):
            return media

    if looks_like_html(body_prefix):
        return media or "text/html"

    raise InvalidContentTypeError(
        f"Content-Type '{media or 'unknown'}' is not an HTML document.",
    )


def assert_content_length_within_limit(
    content_length_header: str | None,
    *,
    max_bytes: int,
) -> int | None:
    """
    Parse Content-Length and reject if declared size exceeds ``max_bytes``.

    Returns parsed length or None if header absent/invalid.
    """
    if content_length_header is None or content_length_header.strip() == "":
        return None
    try:
        length = int(content_length_header.strip())
    except ValueError:
        return None
    if length < 0:
        return None
    if length > max_bytes:
        raise DownloadTooLargeError(
            f"Content-Length {length} exceeds maximum of {max_bytes} bytes.",
        )
    return length


def assert_public_crawl_url(url: str) -> None:
    """
    SSRF guard for request and redirect targets.

    Blocks non-http(s) schemes, credentials, blocked hostnames, and private IP literals.
    Does not perform DNS (hostname denylist + literal IP checks only).
    """
    parsed = urlparse(url)
    scheme = (parsed.scheme or "").lower()
    if scheme not in {"http", "https"}:
        raise SsrfBlockedError(f"Scheme '{scheme or 'missing'}' is not allowed for crawl.")
    if parsed.username is not None or parsed.password is not None:
        raise SsrfBlockedError("Crawl URL must not include credentials.")
    host = parsed.hostname
    if not host:
        raise SsrfBlockedError("Crawl URL host is missing.")

    host_lower = host.lower().rstrip(".")
    if is_blocked_hostname(host_lower):
        raise SsrfBlockedError(f"Host '{host_lower}' is not a public internet target.")

    try:
        ipaddress.ip_address(host_lower.strip("[]"))
        is_ip = True
    except ValueError:
        is_ip = False

    if is_ip and not is_public_ip(host_lower):
        raise SsrfBlockedError(f"IP '{host_lower}' is not a public internet target.")


def resolve_redirect_url(current_url: str, location: str | None) -> str:
    """Resolve a Location header against the current URL."""
    if location is None or not str(location).strip():
        raise InvalidRedirectError("Redirect response missing Location header.")
    target = urljoin(current_url, location.strip())
    assert_public_crawl_url(target)
    return target

"""Website URL value object — DOMAIN_MODEL Website URL / Canonical URL."""

from __future__ import annotations

from dataclasses import dataclass
from urllib.parse import urlparse, urlunparse

from app.domain.exceptions import DomainValidationError


@dataclass(frozen=True, slots=True)
class WebsiteUrl:
    """Normalized public website URL (HTTPS-only for Sprint 2 intake)."""

    original_url: str
    canonical_url: str
    host: str
    is_https: bool

    @property
    def domain(self) -> str:
        """Extract registrable-looking host without leading www."""
        host = self.host.lower()
        if host.startswith("www."):
            return host[4:]
        return host


def extract_domain(host: str) -> str:
    cleaned = host.strip().lower()
    if cleaned.startswith("www."):
        return cleaned[4:]
    return cleaned


def normalize_website_url(raw: str, *, require_https: bool = True) -> WebsiteUrl:
    """
    Validate and normalize a website URL.

    Rules (Sprint 2 + DOMAIN_MODEL):
    - URL required
    - HTTPS required by default (user Sprint 2 requirement)
    - Host required; no credentials
    - Canonical form: lowercase scheme/host, no fragment, strip default ports,
      strip trailing slash on path (except keep empty path as "")
    """
    if raw is None or not str(raw).strip():
        raise DomainValidationError("URL is required", code="URL_REQUIRED")

    candidate = str(raw).strip()
    if "://" not in candidate:
        candidate = f"https://{candidate}"

    parsed = urlparse(candidate)
    scheme = (parsed.scheme or "").lower()
    if scheme not in {"http", "https"}:
        raise DomainValidationError("URL scheme must be http or https", code="URL_SCHEME_INVALID")

    if require_https and scheme != "https":
        raise DomainValidationError("URL must use HTTPS", code="URL_HTTPS_REQUIRED")

    if parsed.username or parsed.password:
        raise DomainValidationError("URL must not include credentials", code="URL_CREDENTIALS")

    host = (parsed.hostname or "").lower().rstrip(".")
    if not host or "." not in host:
        raise DomainValidationError(
            "URL must include a valid public domain",
            code="URL_HOST_INVALID",
        )

    if host in {"localhost"} or host.endswith(".local"):
        raise DomainValidationError("Localhost URLs are not allowed", code="URL_HOST_BLOCKED")

    path = parsed.path or ""
    if path == "/" or path.endswith("/"):
        path = path.rstrip("/")

    # Drop default ports
    netloc = host
    if parsed.port and not (
        (scheme == "https" and parsed.port == 443) or (scheme == "http" and parsed.port == 80)
    ):
        netloc = f"{host}:{parsed.port}"

    canonical = urlunparse((scheme, netloc, path, "", parsed.query, ""))
    original = str(raw).strip()

    return WebsiteUrl(
        original_url=original,
        canonical_url=canonical,
        host=host,
        is_https=scheme == "https",
    )

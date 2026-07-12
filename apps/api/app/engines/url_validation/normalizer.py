"""URL normalization and canonicalization (ENGINE_SPEC §6.6 / §6.7).

Rules applied in order:
1. Trim whitespace.
2. Reject blocked schemes early (javascript:, data:, file:, …).
3. If scheme missing, prepend ``https://``.
4. Parse with ``urllib.parse``.
5. Lowercase scheme and host; IDNA-encode host (Unicode → punycode).
6. Remove default ports (:80 / :443).
7. Collapse duplicate path slashes; origin-only path becomes ``/``.
8. Strip fragments (never sent to servers).
9. Preserve query string as provided.
10. Reject credentials in userinfo.
"""

from __future__ import annotations

import ipaddress
import re
from urllib.parse import quote, unquote, urlparse, urlunparse

import idna
import tldextract

from app.engines.url_validation.constants import ALLOWED_SCHEMES, BLOCKED_SCHEMES, MAX_URL_LENGTH
from app.engines.url_validation.domain import UrlParts
from app.engines.url_validation.exceptions import (
    InvalidSchemeError,
    MalformedUrlError,
    UnsupportedProtocolError,
)
from app.engines.url_validation.validators import is_blocked_hostname

# Detect scheme-like prefix without regex-heavy URL parsing.
_SCHEME_PREFIX = re.compile(r"^([a-zA-Z][a-zA-Z0-9+.-]*):")

# Shared extractor; uses bundled public suffix list (no network at import).
_EXTRACTOR = tldextract.TLDExtract(suffix_list_urls=(), cache_dir=None)


def _detect_raw_scheme(raw: str) -> str | None:
    match = _SCHEME_PREFIX.match(raw)
    if match is None:
        return None
    return match.group(1).lower()


def _collapse_path(path: str) -> str:
    if not path:
        return "/"
    # Decode once for slash collapsing, then re-encode unsafe chars conservatively.
    decoded = unquote(path)
    parts = [segment for segment in decoded.split("/") if segment != ""]
    collapsed = "/" + "/".join(parts) if parts else "/"
    # Keep trailing slash only for origin root (always "/"); strip for resource paths.
    if collapsed != "/" and decoded.endswith("/") and not parts:
        return "/"
    return quote(collapsed, safe="/:@-._~!$&'()*+,;=")


def _is_ip_literal(host: str) -> bool:
    candidate = host.strip("[]")
    try:
        ipaddress.ip_address(candidate)
        return True
    except ValueError:
        return False


def _idna_encode_host(host: str) -> tuple[str, str]:
    """Return (punycode_hostname, unicode_hostname)."""
    if _is_ip_literal(host):
        cleaned = host.strip("[]").lower()
        return cleaned, cleaned

    # Strip trailing dots (FQDN form).
    cleaned = host.rstrip(".").lower()
    try:
        # idna expects unicode labels; decode punycode first if needed.
        unicode_host = idna.decode(cleaned)
        ascii_host = idna.encode(unicode_host).decode("ascii")
    except (idna.IDNAError, UnicodeError) as exc:
        raise MalformedUrlError(
            "Hostname contains invalid internationalized domain characters.",
            code="INVALID_URL",
        ) from exc
    return ascii_host, unicode_host


def _split_domain(hostname: str, *, is_ip: bool) -> tuple[str, str | None]:
    if is_ip:
        return hostname, None

    ext = _EXTRACTOR(hostname)
    if ext.domain and ext.suffix:
        root = f"{ext.domain}.{ext.suffix}".lower()
        subdomain = ext.subdomain.lower() if ext.subdomain else None
        return root, subdomain

    # Fallback when PSL cannot classify (e.g. single-label — usually invalid later).
    return hostname.lower(), None


def normalize_url(raw_url: str) -> UrlParts:
    """
    Normalize and canonicalize a user-supplied URL string into ``UrlParts``.

    Raises:
        MalformedUrlError: empty, too long, unparsable, missing host, bad IDN
        UnsupportedProtocolError: blocked scheme
        InvalidSchemeError: scheme not http/https
    """
    if raw_url is None:
        raise MalformedUrlError("URL is required.", code="URL_REQUIRED")

    original = str(raw_url).strip()
    if not original:
        raise MalformedUrlError("URL is required.", code="URL_REQUIRED")

    if len(original) > MAX_URL_LENGTH:
        raise MalformedUrlError(
            f"URL exceeds maximum length of {MAX_URL_LENGTH} characters.",
            code="URL_TOO_LONG",
        )

    raw_scheme = _detect_raw_scheme(original)
    if raw_scheme is not None and raw_scheme in BLOCKED_SCHEMES:
        raise UnsupportedProtocolError(
            f"Protocol '{raw_scheme}:' is not allowed.",
            code="INVALID_SCHEME",
        )

    candidate = original
    if raw_scheme is None:
        candidate = f"https://{original}"
    elif raw_scheme not in ALLOWED_SCHEMES and raw_scheme not in BLOCKED_SCHEMES:
        # Unknown schemes (e.g. chrome-extension) still rejected.
        raise UnsupportedProtocolError(
            f"Protocol '{raw_scheme}:' is not allowed.",
            code="INVALID_SCHEME",
        )

    parsed = urlparse(candidate)
    scheme = (parsed.scheme or "").lower()

    if scheme in BLOCKED_SCHEMES:
        raise UnsupportedProtocolError(
            f"Protocol '{scheme}:' is not allowed.",
            code="INVALID_SCHEME",
        )
    if scheme not in ALLOWED_SCHEMES:
        raise InvalidSchemeError(
            "URL scheme must be http or https.",
            code="INVALID_SCHEME",
        )

    if parsed.username is not None or parsed.password is not None:
        raise MalformedUrlError(
            "URL must not include credentials.",
            code="CREDENTIALS_NOT_ALLOWED",
        )

    host_raw = parsed.hostname
    if host_raw is None or host_raw == "":
        raise MalformedUrlError("URL host is missing.", code="INVALID_URL")

    is_ip = _is_ip_literal(host_raw)
    try:
        hostname, hostname_unicode = _idna_encode_host(host_raw)
    except MalformedUrlError:
        raise

    if not is_ip and "." not in hostname and not is_blocked_hostname(hostname):
        raise MalformedUrlError(
            "URL must include a valid public domain.",
            code="INVALID_URL",
        )
    # Bracket IPv6 in netloc when needed.
    if is_ip:
        try:
            ip_obj = ipaddress.ip_address(hostname)
        except ValueError as exc:
            raise MalformedUrlError("IP literal host is invalid.", code="INVALID_URL") from exc
        host_for_netloc = f"[{hostname}]" if ip_obj.version == 6 else hostname
    else:
        host_for_netloc = hostname

    port = parsed.port
    default_port = 443 if scheme == "https" else 80
    if port == default_port:
        port = None

    fragment_stripped = bool(parsed.fragment)
    path = _collapse_path(parsed.path or "")
    query = parsed.query  # preserved as provided

    if port is None:
        netloc = host_for_netloc
    else:
        netloc = f"{host_for_netloc}:{port}"

    normalized = urlunparse((scheme, netloc, path, "", query, ""))
    root_domain, subdomain = _split_domain(hostname, is_ip=is_ip)

    return UrlParts(
        original_url=original,
        normalized_url=normalized,
        scheme=scheme,
        hostname=hostname,
        hostname_unicode=hostname_unicode,
        root_domain=root_domain,
        subdomain=subdomain,
        port=port if port is not None else default_port,
        path=path,
        query=query,
        is_https=scheme == "https",
        is_ip=is_ip,
        fragment_stripped=fragment_stripped,
    )

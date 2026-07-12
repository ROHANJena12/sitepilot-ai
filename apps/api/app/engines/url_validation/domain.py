"""Domain value objects for parsed / normalized URL components."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class UrlParts:
    """Immutable parsed URL parts after normalization (pre-SSRF / DNS)."""

    original_url: str
    normalized_url: str
    scheme: str
    hostname: str
    hostname_unicode: str
    root_domain: str
    subdomain: str | None
    port: int | None
    path: str
    query: str
    is_https: bool
    is_ip: bool
    fragment_stripped: bool

"""Constants and denylists for URL Validation (ENGINE_SPEC §6.5 / §6.13)."""

from __future__ import annotations

from typing import Final

# Maximum accepted raw URL length (ENGINE_SPEC §6.12).
MAX_URL_LENGTH: Final[int] = 2048

# Allowed wire schemes after normalization.
ALLOWED_SCHEMES: Final[frozenset[str]] = frozenset({"http", "https"})

# Explicitly rejected schemes / pseudo-protocols (security).
# Rule: never allow non-HTTP transports or script/data handlers.
BLOCKED_SCHEMES: Final[frozenset[str]] = frozenset(
    {
        "file",
        "ftp",
        "ssh",
        "javascript",
        "data",
        "blob",
        "chrome",
        "about",
        "mailto",
        "tel",
        "ws",
        "wss",
        "gopher",
        "dict",
        "ldap",
        "sftp",
    }
)

# Hostnames that must never be fetched (SSRF / loopback).
BLOCKED_HOSTNAMES: Final[frozenset[str]] = frozenset(
    {
        "localhost",
        "localhost.localdomain",
        "ip6-localhost",
        "ip6-loopback",
        "metadata.google.internal",
        "metadata.goog",
        "instance-data",
    }
)

# Suffixes treated as non-public / lab-only.
BLOCKED_HOST_SUFFIXES: Final[tuple[str, ...]] = (
    ".local",
    ".localhost",
    ".internal",
    ".intranet",
    ".corp",
    ".home",
    ".lan",
)

# DNS lookup defaults (ENGINE_SPEC §6.10 DNS = 2s).
DEFAULT_DNS_TIMEOUT_SECONDS: Final[float] = 2.0

ENGINE_NAME: Final[str] = "url_validation"
SCHEMA_VERSION: Final[str] = "engine.url_validation.output.v1"

"""Security Intelligence Engine constants."""

from __future__ import annotations

from typing import Final

ENGINE_NAME: Final[str] = "security"
SCHEMA_VERSION: Final[str] = "engine.security.output.v1"

# Expected security response headers (lowercase).
SECURITY_HEADERS: Final[tuple[str, ...]] = (
    "content-security-policy",
    "strict-transport-security",
    "x-frame-options",
    "x-content-type-options",
    "referrer-policy",
    "permissions-policy",
    "cross-origin-resource-policy",
    "cross-origin-embedder-policy",
    "cross-origin-opener-policy",
)

HSTS_MIN_MAX_AGE: Final[int] = 15_552_000  # 180 days (ENGINE_SPEC §11.4)

INLINE_SCRIPT_LARGE_BYTES: Final[int] = 10_240  # 10 KiB

SENSITIVE_INPUT_TYPES: Final[frozenset[str]] = frozenset(
    {"password", "email", "tel", "credit-card", "cc-number"}
)

SENSITIVE_PATH_HINTS: Final[tuple[str, ...]] = (
    "/admin",
    "/wp-admin",
    "/.env",
    "/.git",
    "/backup",
    "/phpmyadmin",
    "/config",
    "/server-status",
)

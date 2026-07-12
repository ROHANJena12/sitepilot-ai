"""URL-safe HMAC signed tokens (stdlib — no extra dependency)."""

from __future__ import annotations

import base64
import hashlib
import hmac
import json
import time
from typing import Any


class TokenError(Exception):
    """Base signed-token error."""


class TokenInvalidError(TokenError):
    """Missing, malformed, or tampered token."""


class TokenExpiredError(TokenError):
    """Token past its expiry."""


def _b64encode(raw: bytes) -> str:
    return base64.urlsafe_b64encode(raw).decode("ascii").rstrip("=")


def _b64decode(value: str) -> bytes:
    pad = "=" * (-len(value) % 4)
    return base64.urlsafe_b64decode(value + pad)


def sign_payload(
    payload: dict[str, Any],
    *,
    secret: str,
    salt: str,
    ttl_seconds: int,
) -> tuple[str, int]:
    """
    Return ``(token, expires_at_unix)``.

    Token format: ``{b64url(json)}.{b64url(hmac_sha256)}``.
    """
    if ttl_seconds < 1:
        raise ValueError("ttl_seconds must be >= 1")
    expires_at = int(time.time()) + int(ttl_seconds)
    body = dict(payload)
    body["exp"] = expires_at
    body_bytes = json.dumps(body, separators=(",", ":"), sort_keys=True).encode("utf-8")
    body_b64 = _b64encode(body_bytes)
    digest = hmac.new(
        f"{salt}:{secret}".encode("utf-8"),
        body_b64.encode("ascii"),
        hashlib.sha256,
    ).digest()
    return f"{body_b64}.{_b64encode(digest)}", expires_at


def verify_token(
    token: str,
    *,
    secret: str,
    salt: str,
) -> dict[str, Any]:
    """
    Verify signature and expiry; return payload dict (includes ``exp``).

    Raises ``TokenInvalidError`` or ``TokenExpiredError``.
    """
    if not token or "." not in token:
        raise TokenInvalidError("Malformed share token.")
    body_b64, _, sig_b64 = token.partition(".")
    if not body_b64 or not sig_b64 or "." in sig_b64:
        raise TokenInvalidError("Malformed share token.")
    expected = hmac.new(
        f"{salt}:{secret}".encode("utf-8"),
        body_b64.encode("ascii"),
        hashlib.sha256,
    ).digest()
    try:
        provided = _b64decode(sig_b64)
    except Exception as exc:  # noqa: BLE001
        raise TokenInvalidError("Malformed share token.") from exc
    if not hmac.compare_digest(expected, provided):
        raise TokenInvalidError("Invalid share token.")
    try:
        payload = json.loads(_b64decode(body_b64).decode("utf-8"))
    except Exception as exc:  # noqa: BLE001
        raise TokenInvalidError("Malformed share token.") from exc
    if not isinstance(payload, dict):
        raise TokenInvalidError("Malformed share token.")
    exp = payload.get("exp")
    if not isinstance(exp, int):
        raise TokenInvalidError("Malformed share token.")
    if int(time.time()) >= exp:
        raise TokenExpiredError("Share link has expired.")
    return payload

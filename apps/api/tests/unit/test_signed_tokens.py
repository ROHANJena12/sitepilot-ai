"""Unit tests for HMAC signed share tokens."""

from __future__ import annotations

import time

import pytest

from app.core.signed_tokens import (
    TokenExpiredError,
    TokenInvalidError,
    sign_payload,
    verify_token,
)

SECRET = "test-secret"
SALT = "test-salt"


def test_sign_and_verify_roundtrip() -> None:
    token, exp = sign_payload(
        {"aid": "11111111-1111-1111-1111-111111111111"},
        secret=SECRET,
        salt=SALT,
        ttl_seconds=3600,
    )
    assert exp > int(time.time())
    payload = verify_token(token, secret=SECRET, salt=SALT)
    assert payload["aid"] == "11111111-1111-1111-1111-111111111111"
    assert payload["exp"] == exp


def test_tampered_token_rejected() -> None:
    token, _ = sign_payload({"aid": "a"}, secret=SECRET, salt=SALT, ttl_seconds=60)
    body, _, sig = token.partition(".")
    tampered = f"{body}x.{sig}"
    with pytest.raises(TokenInvalidError):
        verify_token(tampered, secret=SECRET, salt=SALT)


def test_wrong_secret_rejected() -> None:
    token, _ = sign_payload({"aid": "a"}, secret=SECRET, salt=SALT, ttl_seconds=60)
    with pytest.raises(TokenInvalidError):
        verify_token(token, secret="other", salt=SALT)


def test_expired_token_rejected() -> None:
    token, _ = sign_payload({"aid": "a"}, secret=SECRET, salt=SALT, ttl_seconds=60)
    # Force expiry by rewriting payload with past exp (invalid sig path) —
    # instead call verify after signing with ttl then monkeypatch time.
    body_b64, _, _sig = token.partition(".")
    # Build an expired-but-valid token by signing with negative skew via direct API:
    # sign then verify with clock moved forward.
    expired_token, _ = sign_payload({"aid": "a"}, secret=SECRET, salt=SALT, ttl_seconds=60)
    # Manually craft: use verify after waiting is slow; instead sign with ttl=60 and
    # patch time.time in verify by constructing payload with past exp properly signed.
    import base64
    import hashlib
    import hmac
    import json

    past = int(time.time()) - 10
    body = json.dumps({"aid": "a", "exp": past}, separators=(",", ":"), sort_keys=True).encode()
    body_b64 = base64.urlsafe_b64encode(body).decode().rstrip("=")
    digest = hmac.new(f"{SALT}:{SECRET}".encode(), body_b64.encode(), hashlib.sha256).digest()
    sig = base64.urlsafe_b64encode(digest).decode().rstrip("=")
    with pytest.raises(TokenExpiredError):
        verify_token(f"{body_b64}.{sig}", secret=SECRET, salt=SALT)


def test_malformed_token_rejected() -> None:
    with pytest.raises(TokenInvalidError):
        verify_token("not-a-token", secret=SECRET, salt=SALT)
    with pytest.raises(TokenInvalidError):
        verify_token("", secret=SECRET, salt=SALT)

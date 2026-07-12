"""Domain URL validation tests (no database)."""

from __future__ import annotations

import pytest

from app.domain.exceptions import DomainValidationError
from app.domain.website_url import extract_domain, normalize_website_url


def test_normalize_https_url() -> None:
    parsed = normalize_website_url("HTTPS://WWW.Example.COM/Path/")
    assert parsed.canonical_url == "https://www.example.com/Path"
    assert parsed.host == "www.example.com"
    assert parsed.is_https is True
    assert parsed.domain == "example.com"


def test_normalize_adds_https_when_missing_scheme() -> None:
    parsed = normalize_website_url("contoso.com")
    assert parsed.canonical_url == "https://contoso.com"
    assert parsed.is_https is True


def test_reject_http_when_https_required() -> None:
    with pytest.raises(DomainValidationError) as exc:
        normalize_website_url("http://example.com", require_https=True)
    assert exc.value.code == "URL_HTTPS_REQUIRED"


def test_extract_domain_strips_www() -> None:
    assert extract_domain("www.example.com") == "example.com"


def test_reject_empty_url() -> None:
    with pytest.raises(DomainValidationError) as exc:
        normalize_website_url("   ")
    assert exc.value.code == "URL_REQUIRED"

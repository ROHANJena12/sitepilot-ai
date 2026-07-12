"""Unit tests for URL Validation Engine (ENGINE_SPEC §6 / Sprint 4)."""

from __future__ import annotations

import pytest

from app.engines.url_validation import validate_url
from app.engines.url_validation.exceptions import DnsResolutionError
from app.engines.url_validation.normalizer import normalize_url
from app.engines.url_validation.validators import is_public_ip


def _public_dns(hostname: str, timeout: float) -> list[str]:
    return ["93.184.216.34"]


def _fail_dns(hostname: str, timeout: float) -> list[str]:
    raise DnsResolutionError("DNS resolution failed for hostname.")


class TestHappyPath:
    def test_https_openai(self) -> None:
        result = validate_url("https://openai.com", dns_lookup=_public_dns)
        assert result.valid is True
        assert result.scheme == "https"
        assert result.hostname == "openai.com"
        assert result.is_https is True
        assert result.is_public is True
        assert result.dns_resolved is True
        assert result.normalized_url == "https://openai.com/"

    def test_http_example(self) -> None:
        result = validate_url("http://example.com", dns_lookup=_public_dns)
        assert result.valid is True
        assert result.is_https is False
        assert "HTTP_NOT_HTTPS" in result.warnings
        assert result.normalized_url == "http://example.com/"

    def test_scheme_omitted_defaults_https(self) -> None:
        result = validate_url("example.com", dns_lookup=_public_dns)
        assert result.valid is True
        assert result.scheme == "https"
        assert result.normalized_url == "https://example.com/"

    def test_trailing_slash_origin(self) -> None:
        result = validate_url("https://example.com/", dns_lookup=_public_dns)
        assert result.valid is True
        assert result.normalized_url == "https://example.com/"

    def test_multiple_trailing_slashes(self) -> None:
        result = validate_url("https://example.com////", dns_lookup=_public_dns)
        assert result.valid is True
        assert result.normalized_url == "https://example.com/"

    def test_uppercase_host_lowercased(self) -> None:
        result = validate_url("https://WWW.OpenAI.COM", dns_lookup=_public_dns)
        assert result.valid is True
        assert result.hostname == "www.openai.com"
        assert result.subdomain == "www"
        assert result.root_domain == "openai.com"
        assert result.normalized_url == "https://www.openai.com/"

    def test_idn_unicode(self) -> None:
        result = validate_url("https://bücher.de", dns_lookup=_public_dns)
        assert result.valid is True
        assert result.hostname == "xn--bcher-kva.de"

    def test_idn_punycode(self) -> None:
        result = validate_url("https://xn--bcher-kva.de", dns_lookup=_public_dns)
        assert result.valid is True
        assert result.hostname == "xn--bcher-kva.de"

    def test_default_https_port_stripped(self) -> None:
        result = validate_url("https://google.com:443", dns_lookup=_public_dns)
        assert result.valid is True
        assert result.normalized_url == "https://google.com/"
        assert result.port == 443

    def test_non_default_port_preserved(self) -> None:
        result = validate_url("https://google.com:8443", dns_lookup=_public_dns)
        assert result.valid is True
        assert result.normalized_url == "https://google.com:8443/"
        assert result.port == 8443

    def test_leading_trailing_spaces(self) -> None:
        result = validate_url("  https://example.com  ", dns_lookup=_public_dns)
        assert result.valid is True
        assert result.original_url == "https://example.com"

    def test_uppercase_scheme(self) -> None:
        result = validate_url("HTTPS://Example.COM/Path", dns_lookup=_public_dns)
        assert result.valid is True
        assert result.scheme == "https"
        assert result.hostname == "example.com"
        assert result.normalized_url == "https://example.com/Path"


class TestSsrfAndPrivate:
    @pytest.mark.parametrize(
        "url",
        [
            "localhost",
            "http://localhost",
            "https://localhost/admin",
            "https://127.0.0.1",
            "http://127.0.0.1",
            "https://0.0.0.0",
            "https://192.168.1.1",
            "https://10.0.0.5",
            "https://172.16.0.1",
            "https://[::1]/",
            "https://169.254.169.254/latest/meta-data",
            "https://metadata.google.internal",
            "https://foo.local",
        ],
    )
    def test_private_and_loopback_blocked(self, url: str) -> None:
        result = validate_url(url, resolve_dns=False)
        assert result.valid is False
        assert result.validation_errors[0].code == "SSRF_BLOCKED"


class TestBlockedSchemes:
    @pytest.mark.parametrize(
        "url",
        [
            "file:///etc/passwd",
            "javascript:alert(1)",
            "ftp://example.com",
            "data:text/html,hi",
            "blob:https://example.com/uuid",
            "chrome://settings",
            "about:blank",
            "ssh://example.com",
        ],
    )
    def test_unsupported_protocols(self, url: str) -> None:
        result = validate_url(url, resolve_dns=False)
        assert result.valid is False
        assert result.validation_errors[0].code == "INVALID_SCHEME"


class TestMalformed:
    @pytest.mark.parametrize(
        "url",
        [
            "abcd",
            "https://",
            "",
            "   ",
            "https://exa mple.com",
        ],
    )
    def test_malformed_urls(self, url: str) -> None:
        result = validate_url(url, resolve_dns=False)
        assert result.valid is False
        assert result.validation_errors[0].code in {
            "INVALID_URL",
            "URL_REQUIRED",
        }

    def test_invalid_unicode_hostname(self) -> None:
        result = validate_url("https://xn--zzz-.de", resolve_dns=False)
        assert result.valid is False

    def test_credentials_rejected(self) -> None:
        result = validate_url("https://user:pass@example.com", resolve_dns=False)
        assert result.valid is False
        assert result.validation_errors[0].code == "CREDENTIALS_NOT_ALLOWED"

    def test_too_long(self) -> None:
        result = validate_url("https://example.com/" + ("a" * 2100), resolve_dns=False)
        assert result.valid is False
        assert result.validation_errors[0].code == "URL_TOO_LONG"


class TestDns:
    def test_dns_failure(self) -> None:
        result = validate_url("https://example.com", dns_lookup=_fail_dns)
        assert result.valid is False
        assert result.validation_errors[0].code == "DNS_FAILURE"
        assert result.dns_resolved is False

    def test_dns_resolves_to_private_blocked(self) -> None:
        def private_dns(hostname: str, timeout: float) -> list[str]:
            return ["10.0.0.8"]

        result = validate_url("https://example.com", dns_lookup=private_dns)
        assert result.valid is False
        assert result.validation_errors[0].code == "SSRF_BLOCKED"

    def test_skip_dns(self) -> None:
        result = validate_url("https://example.com", resolve_dns=False)
        assert result.valid is True
        assert result.dns_resolved is False
        assert result.resolved_ips == ()


class TestPublicIpHelper:
    @pytest.mark.parametrize(
        ("address", "expected"),
        [
            ("8.8.8.8", True),
            ("93.184.216.34", True),
            ("127.0.0.1", False),
            ("0.0.0.0", False),
            ("10.0.0.5", False),
            ("192.168.1.1", False),
            ("172.16.0.1", False),
            ("169.254.1.1", False),
            ("::1", False),
            ("fc00::1", False),
            ("fe80::1", False),
            # RFC 6052 NAT64 well-known prefix 64:ff9b::/96 — judge by embedded IPv4
            ("64:ff9b::808:808", True),  # embeds 8.8.8.8
            ("64:ff9b::c6ca:b029", True),  # embeds 198.202.176.41 (stripe.com-style)
            ("64:ff9b::a00:1", False),  # embeds 10.0.0.1
            ("64:ff9b::7f00:1", False),  # embeds 127.0.0.1
            ("64:ff9b::a9fe:a9fe", False),  # embeds 169.254.169.254
            ("64:ff9b::c0a8:101", False),  # embeds 192.168.1.1
        ],
    )
    def test_is_public_ip(self, address: str, expected: bool) -> None:
        assert is_public_ip(address) is expected


class TestNat64DnsRegression:
    """DNS64/NAT64 AAAA must not fail validation when embedded IPv4 is public."""

    def test_stripe_style_nat64_aaaa_with_public_a_passes(self) -> None:
        def dns64_lookup(hostname: str, timeout: float) -> list[str]:
            return [
                "198.202.176.41",
                "64:ff9b::c6ca:b029",  # NAT64 of 198.202.176.41
            ]

        result = validate_url("https://stripe.com", dns_lookup=dns64_lookup)
        assert result.valid is True
        assert result.dns_resolved is True
        assert "64:ff9b::c6ca:b029" in result.resolved_ips

    def test_nat64_with_private_embedded_ipv4_fails(self) -> None:
        def dns64_private(hostname: str, timeout: float) -> list[str]:
            return ["64:ff9b::a00:1"]  # embeds 10.0.0.1

        result = validate_url("https://example.com", dns_lookup=dns64_private)
        assert result.valid is False
        assert result.validation_errors[0].code == "SSRF_BLOCKED"


class TestNormalizerUnit:
    def test_fragment_stripped(self) -> None:
        parts = normalize_url("https://example.com/path#section")
        assert parts.fragment_stripped is True
        assert "#" not in parts.normalized_url

    def test_query_preserved(self) -> None:
        parts = normalize_url("https://example.com/?b=2&a=1")
        assert parts.query == "b=2&a=1"
        assert "b=2&a=1" in parts.normalized_url

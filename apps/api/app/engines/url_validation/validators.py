"""Security and host validators for URL Validation (ENGINE_SPEC §6.13).

Security restrictions (SSRF):
- Block localhost / loopback hostnames and ``*.local`` (and related suffixes).
- Block private, loopback, link-local, reserved, multicast, and unspecified IPs.
- Block cloud metadata addresses (e.g. 169.254.169.254).
- Require DNS to resolve to public addresses only (when DNS is enabled).
- Exception: RFC 6052 NAT64 ``64:ff9b::/96`` is judged by its embedded IPv4.

This module never performs HTTP. DNS is optional and injectable for tests.
"""

from __future__ import annotations

import ipaddress
from collections.abc import Callable, Sequence
from typing import Protocol

import dns.exception
import dns.resolver

from app.engines.url_validation.constants import (
    BLOCKED_HOST_SUFFIXES,
    BLOCKED_HOSTNAMES,
    DEFAULT_DNS_TIMEOUT_SECONDS,
)
from app.engines.url_validation.exceptions import DnsResolutionError, PrivateAddressError

DnsLookupFn = Callable[[str, float], Sequence[str]]

# RFC 6052 well-known NAT64/DNS64 prefix. Python marks these as ``is_reserved``
# even when they embed a public IPv4; we validate the embedded v4 instead.
_NAT64_WELL_KNOWN_PREFIX = ipaddress.IPv6Network("64:ff9b::/96")


class SupportsDnsLookup(Protocol):
    def __call__(self, hostname: str, timeout: float) -> Sequence[str]: ...


def is_blocked_hostname(hostname: str) -> bool:
    """Return True if hostname is denylisted (localhost, metadata, .local, …)."""
    host = hostname.strip(".").lower()
    if host in BLOCKED_HOSTNAMES:
        return True
    return any(host.endswith(suffix) for suffix in BLOCKED_HOST_SUFFIXES)


def _nat64_embedded_ipv4(ip: ipaddress.IPv6Address) -> ipaddress.IPv4Address | None:
    """
    If ``ip`` is in ``64:ff9b::/96``, return the embedded IPv4 (last 32 bits).

    For the well-known /96 prefix, RFC 6052 places the IPv4 address in bits 96–127.
    """
    if ip not in _NAT64_WELL_KNOWN_PREFIX:
        return None
    return ipaddress.IPv4Address(int(ip) & 0xFFFFFFFF)


def is_public_ip(address: str) -> bool:
    """
    Return True if ``address`` is a globally routable unicast IP.

    Rejects private, loopback, link-local, reserved, multicast, and unspecified.

    Exception: RFC 6052 NAT64 well-known prefix ``64:ff9b::/96`` is evaluated by
    extracting and validating the embedded IPv4 (DNS64 synthesizes these AAAA
    records; Python marks them ``is_reserved`` even when the v4 target is public).
    """
    try:
        ip = ipaddress.ip_address(address.strip("[]"))
    except ValueError:
        return False

    if isinstance(ip, ipaddress.IPv6Address):
        embedded = _nat64_embedded_ipv4(ip)
        if embedded is not None:
            return is_public_ip(str(embedded))

    if (
        ip.is_private
        or ip.is_loopback
        or ip.is_link_local
        or ip.is_reserved
        or ip.is_multicast
        or ip.is_unspecified
    ):
        return False

    # Defense in depth for IPv4 “documentation” / benchmark ranges sometimes
    # classified inconsistently across Python versions.
    if isinstance(ip, ipaddress.IPv4Address):
        if ip in ipaddress.ip_network("0.0.0.0/8"):
            return False
        if ip in ipaddress.ip_network("224.0.0.0/4"):
            return False

    return True


def assert_public_host_or_ip(hostname: str, *, is_ip: bool) -> None:
    """Raise ``PrivateAddressError`` if hostname/IP is not a public target."""
    if is_blocked_hostname(hostname):
        raise PrivateAddressError(
            "Hostname is not a public internet target.",
            code="SSRF_BLOCKED",
        )

    if is_ip and not is_public_ip(hostname):
        raise PrivateAddressError(
            "IP address is not a public internet target.",
            code="SSRF_BLOCKED",
        )


def default_dns_lookup(hostname: str, timeout: float = DEFAULT_DNS_TIMEOUT_SECONDS) -> list[str]:
    """
    Resolve A/AAAA records for ``hostname`` using dnspython.

    Raises:
        DnsResolutionError: NXDOMAIN, timeout, or empty answer set
    """
    resolver = dns.resolver.Resolver()
    resolver.lifetime = timeout
    resolver.timeout = timeout

    addresses: list[str] = []
    saw_nxdomain = False
    errors: list[str] = []

    for rdtype in ("A", "AAAA"):
        try:
            answer = resolver.resolve(hostname, rdtype)
            addresses.extend(str(rdata) for rdata in answer)
        except dns.resolver.NXDOMAIN:
            saw_nxdomain = True
        except dns.resolver.NoAnswer:
            continue
        except dns.exception.Timeout as exc:
            raise DnsResolutionError(
                "DNS resolution timed out.",
                code="DNS_FAILURE",
            ) from exc
        except dns.exception.DNSException as exc:
            errors.append(f"{rdtype}:{exc}")

    if addresses:
        # Preserve order, drop duplicates.
        seen: set[str] = set()
        unique: list[str] = []
        for addr in addresses:
            if addr not in seen:
                seen.add(addr)
                unique.append(addr)
        return unique

    if saw_nxdomain:
        raise DnsResolutionError(
            "Hostname does not exist (NXDOMAIN).",
            code="DNS_FAILURE",
        )
    detail = "; ".join(errors) if errors else "no A/AAAA records"
    raise DnsResolutionError(
        f"DNS resolution failed ({detail}).",
        code="DNS_FAILURE",
    )


def assert_resolved_ips_public(resolved_ips: Sequence[str]) -> None:
    """Raise if any resolved address is non-public (SSRF)."""
    if not resolved_ips:
        raise DnsResolutionError("DNS returned no addresses.", code="DNS_FAILURE")

    for addr in resolved_ips:
        if not is_public_ip(addr):
            raise PrivateAddressError(
                "Resolved address is not a public internet target.",
                code="SSRF_BLOCKED",
            )

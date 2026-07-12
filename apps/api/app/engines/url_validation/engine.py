"""URL Validation Engine public API (ENGINE_SPEC §6).

Pure engine: no database, repositories, FastAPI, or HTTP fetches.
Optional DNS resolution is the only network side effect.
"""

from __future__ import annotations

from collections.abc import Sequence

from app.engines.url_validation.constants import DEFAULT_DNS_TIMEOUT_SECONDS
from app.engines.url_validation.domain import UrlParts
from app.engines.url_validation.exceptions import UrlValidationError
from app.engines.url_validation.normalizer import normalize_url
from app.engines.url_validation.schemas import ValidationErrorItem, ValidationResult
from app.engines.url_validation.validators import (
    DnsLookupFn,
    assert_public_host_or_ip,
    assert_resolved_ips_public,
    default_dns_lookup,
)


def validate_url(
    url: str,
    *,
    resolve_dns: bool = True,
    dns_timeout: float = DEFAULT_DNS_TIMEOUT_SECONDS,
    dns_lookup: DnsLookupFn | None = None,
) -> ValidationResult:
    """
    Validate and normalize a website URL.

    Processing order (fail-fast):
    1. Normalize / canonicalize (syntax, scheme, IDNA, path).
    2. SSRF hostname / literal IP checks.
    3. Optional DNS resolution + public-IP checks.

    Args:
        url: User-supplied URL (scheme may be omitted).
        resolve_dns: When True, resolve hostname and verify public IPs.
            IP-literal hosts skip DNS and are checked directly.
        dns_timeout: DNS lifetime timeout in seconds (default 2s).
        dns_lookup: Optional injectable resolver for tests.

    Returns:
        Immutable ``ValidationResult``. On failure ``valid`` is False and
        ``validation_errors`` contains structured codes (never raises for
        expected validation failures).
    """
    original = "" if url is None else str(url)
    warnings: list[str] = []

    try:
        parts = normalize_url(url)
    except UrlValidationError as exc:
        return ValidationResult(
            valid=False,
            original_url=original.strip() if original else original,
            validation_errors=(
                ValidationErrorItem(code=exc.code, message=exc.message),
            ),
        )

    if not parts.is_https:
        warnings.append("HTTP_NOT_HTTPS")

    try:
        assert_public_host_or_ip(parts.hostname, is_ip=parts.is_ip)
    except UrlValidationError as exc:
        return _failure_from_parts(
            parts,
            warnings=warnings,
            error=ValidationErrorItem(
                code=exc.code,
                message=exc.message,
                details={"host": parts.hostname},
            ),
        )

    resolved_ips: tuple[str, ...] = ()
    dns_resolved = False
    is_public = True

    if parts.is_ip:
        resolved_ips = (parts.hostname,)
        dns_resolved = True
    elif resolve_dns:
        lookup = dns_lookup or default_dns_lookup
        try:
            addresses: Sequence[str] = lookup(parts.hostname, dns_timeout)
            resolved_ips = tuple(addresses)
            assert_resolved_ips_public(resolved_ips)
            dns_resolved = True
        except UrlValidationError as exc:
            return _failure_from_parts(
                parts,
                warnings=warnings,
                error=ValidationErrorItem(
                    code=exc.code,
                    message=exc.message,
                    details={"host": parts.hostname},
                ),
                dns_resolved=False,
                is_public=False if exc.code == "SSRF_BLOCKED" else None,
            )

    return ValidationResult(
        valid=True,
        original_url=parts.original_url,
        normalized_url=parts.normalized_url,
        hostname=parts.hostname,
        root_domain=parts.root_domain,
        subdomain=parts.subdomain,
        scheme=parts.scheme,
        port=parts.port,
        is_https=parts.is_https,
        is_ip=parts.is_ip,
        is_public=is_public,
        dns_resolved=dns_resolved,
        resolved_ips=resolved_ips,
        validation_errors=(),
        warnings=tuple(warnings),
    )


def _failure_from_parts(
    parts: UrlParts,
    *,
    warnings: list[str],
    error: ValidationErrorItem,
    dns_resolved: bool = False,
    is_public: bool | None = False,
) -> ValidationResult:
    return ValidationResult(
        valid=False,
        original_url=parts.original_url,
        normalized_url=parts.normalized_url,
        hostname=parts.hostname,
        root_domain=parts.root_domain,
        subdomain=parts.subdomain,
        scheme=parts.scheme,
        port=parts.port,
        is_https=parts.is_https,
        is_ip=parts.is_ip,
        is_public=is_public,
        dns_resolved=dns_resolved,
        resolved_ips=(),
        validation_errors=(error,),
        warnings=tuple(warnings),
    )

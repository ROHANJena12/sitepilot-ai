"""Adapter wrapping ``validate_url`` as a pipeline ``Engine`` (no logic changes)."""

from __future__ import annotations

import asyncio
import time
from collections.abc import Sequence
from typing import Any

from app.engines.url_validation.constants import ENGINE_NAME
from app.engines.url_validation.engine import validate_url
from app.engines.url_validation.schemas import ValidationResult
from app.engines.url_validation.validators import DnsLookupFn
from app.pipeline.context import AuditContext
from app.pipeline.result import EngineResult


class UrlValidationEngine:
    """
    Pipeline contract adapter for the URL Validation Engine.

    Does not alter validation rules — delegates to ``validate_url`` and maps
    ``ValidationResult`` into ``EngineResult`` + context enrichment.
    """

    def __init__(
        self,
        *,
        resolve_dns: bool = True,
        dns_timeout: float = 2.0,
        dns_lookup: DnsLookupFn | None = None,
    ) -> None:
        self._resolve_dns = resolve_dns
        self._dns_timeout = dns_timeout
        self._dns_lookup = dns_lookup

    @property
    def name(self) -> str:
        return ENGINE_NAME

    async def run(self, context: AuditContext) -> EngineResult:
        started = time.perf_counter()
        validation = await asyncio.to_thread(
            validate_url,
            context.url,
            resolve_dns=self._resolve_dns,
            dns_timeout=self._dns_timeout,
            dns_lookup=self._dns_lookup,
        )
        duration_ms = int((time.perf_counter() - started) * 1000)
        payload = _payload_from_validation(validation)

        if not validation.valid:
            errors = tuple(
                f"{item.code}: {item.message}" for item in validation.validation_errors
            ) or ("INVALID_URL: URL validation failed.",)
            return EngineResult.fail(
                self.name,
                duration_ms=duration_ms,
                errors=errors,
                payload=payload,
                warnings=tuple(validation.warnings),
            )

        # Enrich mutable context for downstream engines.
        context.normalized_url = validation.normalized_url
        context.shared_state[self.name] = payload
        context.metadata.setdefault("url_validation", {})
        context.metadata["url_validation"] = {
            "hostname": validation.hostname,
            "scheme": validation.scheme,
            "is_https": validation.is_https,
            "dns_resolved": validation.dns_resolved,
        }

        return EngineResult.ok(
            self.name,
            duration_ms=duration_ms,
            payload=payload,
            warnings=tuple(validation.warnings),
        )


def _payload_from_validation(validation: ValidationResult) -> dict[str, Any]:
    return {
        "valid": validation.valid,
        "original_url": validation.original_url,
        "normalized_url": validation.normalized_url,
        "hostname": validation.hostname,
        "root_domain": validation.root_domain,
        "subdomain": validation.subdomain,
        "scheme": validation.scheme,
        "port": validation.port,
        "is_https": validation.is_https,
        "is_ip": validation.is_ip,
        "is_public": validation.is_public,
        "dns_resolved": validation.dns_resolved,
        "resolved_ips": list(validation.resolved_ips),
        "validation_errors": [
            {"code": e.code, "message": e.message, "details": e.details}
            for e in validation.validation_errors
        ],
        "warnings": list(validation.warnings),
    }


# Satisfy type checkers that Sequence is used if we expand options later.
_ = Sequence

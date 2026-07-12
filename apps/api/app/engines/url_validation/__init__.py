"""URL Validation Engine — pure, side-effect-free (except optional DNS).

ENGINE_SPEC §6. Sprint 4 intentionally omits HTTP reachability probes;
orchestration may call a probe later. This package never touches DB, repos, or HTTP.
"""

from __future__ import annotations

from app.engines.url_validation.adapter import UrlValidationEngine
from app.engines.url_validation.engine import validate_url
from app.engines.url_validation.exceptions import (
    DnsResolutionError,
    InvalidSchemeError,
    MalformedUrlError,
    PrivateAddressError,
    UnsupportedProtocolError,
    UrlValidationError,
)
from app.engines.url_validation.schemas import ValidationErrorItem, ValidationResult

__all__ = [
    "validate_url",
    "UrlValidationEngine",
    "ValidationResult",
    "ValidationErrorItem",
    "UrlValidationError",
    "InvalidSchemeError",
    "PrivateAddressError",
    "MalformedUrlError",
    "DnsResolutionError",
    "UnsupportedProtocolError",
]

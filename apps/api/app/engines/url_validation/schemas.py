"""Pydantic response models for the URL Validation Engine."""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class ValidationErrorItem(BaseModel):
    """One structured validation failure."""

    model_config = ConfigDict(frozen=True)

    code: str
    message: str
    details: dict[str, Any] = Field(default_factory=dict)


class ValidationResult(BaseModel):
    """
    Immutable outcome of ``validate_url``.

    When ``valid`` is False, ``validation_errors`` explains why. Warnings are
    non-fatal (e.g. HTTP instead of HTTPS).
    """

    model_config = ConfigDict(frozen=True)

    valid: bool
    original_url: str
    normalized_url: str | None = None
    hostname: str | None = None
    root_domain: str | None = None
    subdomain: str | None = None
    scheme: str | None = None
    port: int | None = None
    is_https: bool | None = None
    is_ip: bool | None = None
    is_public: bool | None = None
    dns_resolved: bool = False
    resolved_ips: tuple[str, ...] = ()
    validation_errors: tuple[ValidationErrorItem, ...] = ()
    warnings: tuple[str, ...] = ()

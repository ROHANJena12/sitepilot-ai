"""Organization request/response schemas."""

from __future__ import annotations

from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.domain.organization import (
    validate_organization_name,
    validate_organization_slug,
    validate_organization_status,
    validate_plan_tier,
)


class OrganizationCreate(BaseModel):
    name: str
    slug: str
    plan_tier: str = "free"
    status: str = "active"
    billing_email: str | None = None
    settings: dict[str, Any] = Field(default_factory=dict)

    @field_validator("name")
    @classmethod
    def _name(cls, value: str) -> str:
        return validate_organization_name(value)

    @field_validator("slug")
    @classmethod
    def _slug(cls, value: str) -> str:
        return validate_organization_slug(value)

    @field_validator("plan_tier")
    @classmethod
    def _plan(cls, value: str) -> str:
        return validate_plan_tier(value)

    @field_validator("status")
    @classmethod
    def _status(cls, value: str) -> str:
        return validate_organization_status(value)


class OrganizationUpdate(BaseModel):
    name: str | None = None
    slug: str | None = None
    plan_tier: str | None = None
    status: str | None = None
    billing_email: str | None = None
    settings: dict[str, Any] | None = None

    @field_validator("name")
    @classmethod
    def _name(cls, value: str | None) -> str | None:
        if value is None:
            return value
        return validate_organization_name(value)

    @field_validator("slug")
    @classmethod
    def _slug(cls, value: str | None) -> str | None:
        if value is None:
            return value
        return validate_organization_slug(value)

    @field_validator("plan_tier")
    @classmethod
    def _plan(cls, value: str | None) -> str | None:
        if value is None:
            return value
        return validate_plan_tier(value)

    @field_validator("status")
    @classmethod
    def _status(cls, value: str | None) -> str | None:
        if value is None:
            return value
        return validate_organization_status(value)


class OrganizationResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    name: str
    slug: str
    plan_tier: str
    status: str
    billing_email: str | None
    settings: dict[str, Any]
    created_at: datetime
    updated_at: datetime
    deleted_at: datetime | None

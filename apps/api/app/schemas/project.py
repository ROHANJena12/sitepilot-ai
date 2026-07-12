"""Project request/response schemas."""

from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, field_validator

from app.domain.project import (
    require_organization_id,
    validate_project_name,
    validate_project_slug,
    validate_project_status,
)


class ProjectCreate(BaseModel):
    organization_id: UUID
    name: str
    slug: str
    description: str | None = None
    status: str = "active"
    created_by_user_id: UUID | None = None

    @field_validator("organization_id")
    @classmethod
    def _org(cls, value: UUID) -> UUID:
        return require_organization_id(value)

    @field_validator("name")
    @classmethod
    def _name(cls, value: str) -> str:
        return validate_project_name(value)

    @field_validator("slug")
    @classmethod
    def _slug(cls, value: str) -> str:
        return validate_project_slug(value)

    @field_validator("status")
    @classmethod
    def _status(cls, value: str) -> str:
        return validate_project_status(value)


class ProjectUpdate(BaseModel):
    name: str | None = None
    slug: str | None = None
    description: str | None = None
    status: str | None = None

    @field_validator("name")
    @classmethod
    def _name(cls, value: str | None) -> str | None:
        if value is None:
            return value
        return validate_project_name(value)

    @field_validator("slug")
    @classmethod
    def _slug(cls, value: str | None) -> str | None:
        if value is None:
            return value
        return validate_project_slug(value)

    @field_validator("status")
    @classmethod
    def _status(cls, value: str | None) -> str | None:
        if value is None:
            return value
        return validate_project_status(value)


class ProjectResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    organization_id: UUID
    name: str
    slug: str
    description: str | None
    status: str
    created_by_user_id: UUID | None
    created_at: datetime
    updated_at: datetime
    deleted_at: datetime | None

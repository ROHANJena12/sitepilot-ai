"""Website request/response schemas."""

from __future__ import annotations

from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, PrivateAttr, field_validator, model_validator

from app.domain.website import require_project_id, validate_website_url
from app.domain.website_url import WebsiteUrl


class WebsiteCreate(BaseModel):
    project_id: UUID
    url: str = Field(..., description="Public website URL (HTTPS)")
    technology_stack: list[Any] = Field(default_factory=list)
    language: str | None = None
    country: str | None = None
    industry: str | None = None
    favicon_url: str | None = None
    title_last_seen: str | None = None

    _parsed: WebsiteUrl | None = PrivateAttr(default=None)

    @field_validator("project_id")
    @classmethod
    def _project(cls, value: UUID) -> UUID:
        return require_project_id(value)

    @model_validator(mode="after")
    def _normalize_url(self) -> WebsiteCreate:
        self._parsed = validate_website_url(self.url)
        return self

    @property
    def parsed(self) -> WebsiteUrl:
        assert self._parsed is not None
        return self._parsed


class WebsiteUpdate(BaseModel):
    url: str | None = None
    technology_stack: list[Any] | None = None
    language: str | None = None
    country: str | None = None
    industry: str | None = None
    favicon_url: str | None = None
    title_last_seen: str | None = None

    _parsed: WebsiteUrl | None = PrivateAttr(default=None)

    @model_validator(mode="after")
    def _normalize_url(self) -> WebsiteUpdate:
        if self.url is not None:
            self._parsed = validate_website_url(self.url)
        return self

    @property
    def parsed(self) -> WebsiteUrl | None:
        return self._parsed


class WebsiteResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    project_id: UUID
    canonical_url: str
    original_url: str
    host: str
    technology_stack: list[Any]
    language: str | None
    country: str | None
    industry: str | None
    favicon_url: str | None
    title_last_seen: str | None
    is_https: bool | None
    created_at: datetime
    updated_at: datetime
    deleted_at: datetime | None

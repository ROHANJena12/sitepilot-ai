"""Immutable crawler result models."""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class RedirectHop(BaseModel):
    """One hop in the redirect chain."""

    model_config = ConfigDict(frozen=True, populate_by_name=True)

    from_url: str = Field(serialization_alias="from", validation_alias="from")
    to_url: str = Field(serialization_alias="to", validation_alias="to")
    status_code: int


class CrawlResult(BaseModel):
    """
    Immutable outcome of a single-page crawl fetch.

    Does not include parsed DOM — body is raw decoded text for downstream engines.
    """

    model_config = ConfigDict(frozen=True)

    original_url: str
    requested_url: str
    final_url: str
    status_code: int
    headers: dict[str, str] = Field(default_factory=dict)
    content_type: str | None = None
    content_length: int | None = None
    response_time_ms: int = Field(ge=0)
    redirects: tuple[RedirectHop, ...] = ()
    body: str = ""
    encoding: str | None = None
    etag: str | None = None
    last_modified: str | None = None
    server: str | None = None
    powered_by: str | None = None
    success: bool
    warnings: tuple[str, ...] = ()
    errors: tuple[str, ...] = ()
    http_version: str | None = None

    def to_payload(self) -> dict[str, Any]:
        """Serialize for ``EngineResult.payload`` / shared_state."""
        data = self.model_dump(mode="python")
        # Prefer ENGINE_SPEC-style redirect keys in payload.
        data["redirects"] = [
            {"from": hop.from_url, "to": hop.to_url, "status_code": hop.status_code}
            for hop in self.redirects
        ]
        return data

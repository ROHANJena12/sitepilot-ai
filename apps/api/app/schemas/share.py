"""Report share schemas (presentation layer only)."""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class ShareLinkResponse(BaseModel):
    """Created share link for a completed audit report."""

    model_config = ConfigDict(extra="forbid")

    share_url: str = Field(description="Absolute URL for the read-only share page")
    token: str = Field(description="Signed share token embedded in share_url")
    expires_at: datetime = Field(description="UTC expiry timestamp")
    audit_id: str = Field(description="Underlying audit UUID")

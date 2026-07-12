"""DTOs for AI generation history (no narrative payloads)."""

from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class GenerationHistoryItem(BaseModel):
    """One immutable generation version (metadata only)."""

    model_config = ConfigDict(frozen=True)

    version: int
    created_at: datetime
    provider: str
    model: str
    prompt_version: str
    schema_version: str
    generation_id: UUID | None = None
    response_hash: str


class GenerationHistoryDTO(BaseModel):
    """Version listing for one AI feature entity under the current report hash."""

    model_config = ConfigDict(frozen=True)

    feature: str
    entity_type: str
    entity_id: str
    audit_id: UUID | None = None
    report_hash: str = ""
    items: list[GenerationHistoryItem] = Field(default_factory=list)

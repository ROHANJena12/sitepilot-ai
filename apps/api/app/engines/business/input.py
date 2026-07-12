"""Business engine input snapshot — upstream analyses only (no Document)."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field

from app.engines.common.findings import Finding


class BusinessInput(BaseModel):
    """
    Immutable snapshot of upstream technical findings.

    Built only from analysis objects in AuditContext.shared_state.
    Never includes Document or HTML.
    """

    model_config = ConfigDict(frozen=True)

    source_findings: tuple[Finding, ...] = ()
    warnings: tuple[str, ...] = ()
    source_counts: dict[str, int] = Field(default_factory=dict)

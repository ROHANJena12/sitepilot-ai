"""Report readiness validation."""

from __future__ import annotations

from app.models.audit_run import AuditRun
from app.services.report.constants import READY_AUDIT_STATUSES
from app.services.report.exceptions import ReportNotReadyError


def assert_audit_ready_for_report(audit: AuditRun) -> None:
    """Raise ReportNotReadyError unless the audit reached a terminal success status."""
    if audit.status not in READY_AUDIT_STATUSES:
        raise ReportNotReadyError(
            f"Audit report is not ready while status is '{audit.status}'.",
            code="REPORT_NOT_READY",
        )


def normalize_category(raw: str | None, *, engine_name: str | None = None) -> str:
    """Map a finding category / engine to a canonical section key."""
    from app.services.report.constants import CATEGORY_ALIASES, ENGINE_TO_CATEGORY

    if raw:
        key = raw.strip().lower().replace("-", "_").replace(" ", "_")
        if key in CATEGORY_ALIASES:
            return CATEGORY_ALIASES[key]
        # Prefix matches (e.g. biz.marketing → business via engine)
        for alias, section in CATEGORY_ALIASES.items():
            if key.startswith(alias):
                return section
    if engine_name and engine_name in ENGINE_TO_CATEGORY:
        return ENGINE_TO_CATEGORY[engine_name]
    return "business"


def derive_rule_id(finding_id: str) -> str:
    """Derive a stable rule_id from finding_id when not persisted."""
    parts = finding_id.split(".")
    if len(parts) >= 2:
        return ".".join(parts[:-1])
    return finding_id

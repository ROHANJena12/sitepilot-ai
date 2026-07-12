"""AuditFinding repository — DATABASE_SPEC §14."""

from __future__ import annotations

from typing import Any
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.audit_finding import AuditFinding


class FindingRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def bulk_create(self, findings: list[AuditFinding]) -> list[AuditFinding]:
        if not findings:
            return []
        self._session.add_all(findings)
        await self._session.flush()
        for row in findings:
            await self._session.refresh(row)
        return findings

    async def create(
        self,
        *,
        audit_run_id: UUID,
        engine_name: str,
        finding_id: str,
        category: str,
        severity: str,
        status: str,
        title: str,
        description: str | None,
        evidence: dict[str, Any] | None = None,
        engine_execution_id: UUID | None = None,
        confidence: int = 100,
    ) -> AuditFinding:
        row = AuditFinding(
            audit_run_id=audit_run_id,
            engine_execution_id=engine_execution_id,
            engine_name=engine_name,
            finding_id=finding_id,
            category=category,
            severity=severity,
            status=status,
            issue=title,
            technical_detail=description,
            evidence=evidence or {},
            confidence=confidence,
        )
        self._session.add(row)
        await self._session.flush()
        await self._session.refresh(row)
        return row

    async def get_by_id(self, finding_row_id: UUID) -> AuditFinding | None:
        """Load a finding by persisted row UUID (``audit_findings.id``)."""
        result = await self._session.execute(
            select(AuditFinding).where(AuditFinding.id == finding_row_id)
        )
        return result.scalar_one_or_none()

    async def list_by_audit(self, audit_run_id: UUID) -> list[AuditFinding]:
        result = await self._session.execute(
            select(AuditFinding)
            .where(AuditFinding.audit_run_id == audit_run_id)
            .order_by(AuditFinding.created_at.asc())
        )
        return list(result.scalars().all())

    async def count_by_severity(self, audit_run_id: UUID) -> dict[str, int]:
        result = await self._session.execute(
            select(AuditFinding.severity, func.count())
            .where(AuditFinding.audit_run_id == audit_run_id)
            .group_by(AuditFinding.severity)
        )
        counts = {sev: 0 for sev in ("critical", "high", "medium", "low", "info")}
        for severity, count in result.all():
            counts[str(severity)] = int(count)
        counts["total"] = sum(v for k, v in counts.items() if k != "total")
        return counts

    async def count_by_engine(self, audit_run_id: UUID) -> dict[str, int]:
        result = await self._session.execute(
            select(AuditFinding.engine_name, func.count())
            .where(AuditFinding.audit_run_id == audit_run_id)
            .group_by(AuditFinding.engine_name)
        )
        return {str(name): int(count) for name, count in result.all()}

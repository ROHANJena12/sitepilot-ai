"""AIGeneration repository — immutable versioned AI artifacts."""

from __future__ import annotations

from typing import Any
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.ai.entity_types import AIEntityType
from app.ai.features import AIFeature
from app.models.ai_generation import AIGeneration


class AIGenerationRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def create(
        self,
        *,
        generation_id: UUID | None,
        feature: AIFeature | str,
        entity_type: AIEntityType | str,
        entity_id: str,
        audit_id: UUID | None,
        provider: str,
        model: str,
        schema_version: str,
        builder_version: int,
        prompt_version: str,
        prompt_hash: str | None,
        report_hash: str | None,
        input_hash: str | None,
        response_hash: str,
        locale: str,
        response_json: dict[str, Any],
        telemetry_json: dict[str, Any] | None,
        diagnostics_json: dict[str, Any] | None,
        status: str,
        version: int,
    ) -> AIGeneration:
        """Insert one immutable generation row (caller supplies ``version``)."""
        row = AIGeneration(
            generation_id=generation_id,
            feature=str(feature),
            entity_type=str(entity_type),
            entity_id=entity_id,
            audit_id=audit_id,
            provider=provider,
            model=model,
            schema_version=schema_version,
            builder_version=builder_version,
            prompt_version=prompt_version,
            prompt_hash=prompt_hash,
            report_hash=report_hash or "",
            input_hash=input_hash,
            response_hash=response_hash,
            locale=locale or "en",
            response_json=response_json,
            telemetry_json=telemetry_json,
            diagnostics_json=diagnostics_json,
            status=status,
            version=version,
        )
        self._session.add(row)
        await self._session.flush()
        await self._session.refresh(row)
        return row

    async def get(self, generation_row_id: UUID) -> AIGeneration | None:
        result = await self._session.execute(
            select(AIGeneration).where(AIGeneration.id == generation_row_id)
        )
        return result.scalar_one_or_none()

    async def get_by_generation_id(self, generation_id: UUID) -> AIGeneration | None:
        result = await self._session.execute(
            select(AIGeneration)
            .where(AIGeneration.generation_id == generation_id)
            .order_by(AIGeneration.version.desc())
            .limit(1)
        )
        return result.scalar_one_or_none()

    async def get_latest(
        self,
        *,
        feature: AIFeature | str,
        entity_id: str,
        report_hash: str | None,
    ) -> AIGeneration | None:
        rh = report_hash or ""
        result = await self._session.execute(
            select(AIGeneration)
            .where(
                AIGeneration.feature == str(feature),
                AIGeneration.entity_id == entity_id,
                AIGeneration.report_hash == rh,
            )
            .order_by(AIGeneration.version.desc())
            .limit(1)
        )
        return result.scalar_one_or_none()

    async def get_by_response_hash(
        self,
        *,
        feature: AIFeature | str,
        entity_id: str,
        report_hash: str | None,
        response_hash: str,
    ) -> AIGeneration | None:
        rh = report_hash or ""
        result = await self._session.execute(
            select(AIGeneration)
            .where(
                AIGeneration.feature == str(feature),
                AIGeneration.entity_id == entity_id,
                AIGeneration.report_hash == rh,
                AIGeneration.response_hash == response_hash,
            )
            .order_by(AIGeneration.version.desc())
            .limit(1)
        )
        return result.scalar_one_or_none()

    async def list_versions(
        self,
        *,
        feature: AIFeature | str,
        entity_id: str,
        report_hash: str | None,
    ) -> list[AIGeneration]:
        rh = report_hash or ""
        result = await self._session.execute(
            select(AIGeneration)
            .where(
                AIGeneration.feature == str(feature),
                AIGeneration.entity_id == entity_id,
                AIGeneration.report_hash == rh,
            )
            .order_by(AIGeneration.version.asc())
        )
        return list(result.scalars().all())

    async def exists(
        self,
        *,
        feature: AIFeature | str,
        entity_id: str,
        report_hash: str | None,
        version: int | None = None,
        response_hash: str | None = None,
    ) -> bool:
        rh = report_hash or ""
        stmt = select(AIGeneration.id).where(
            AIGeneration.feature == str(feature),
            AIGeneration.entity_id == entity_id,
            AIGeneration.report_hash == rh,
        )
        if version is not None:
            stmt = stmt.where(AIGeneration.version == version)
        if response_hash is not None:
            stmt = stmt.where(AIGeneration.response_hash == response_hash)
        result = await self._session.execute(stmt.limit(1))
        return result.scalar_one_or_none() is not None

    async def create_or_reuse(
        self,
        *,
        generation_id: UUID | None,
        feature: AIFeature | str,
        entity_type: AIEntityType | str,
        entity_id: str,
        audit_id: UUID | None,
        provider: str,
        model: str,
        schema_version: str,
        builder_version: int,
        prompt_version: str,
        prompt_hash: str | None,
        report_hash: str | None,
        input_hash: str | None,
        response_hash: str,
        locale: str,
        response_json: dict[str, Any],
        telemetry_json: dict[str, Any] | None,
        diagnostics_json: dict[str, Any] | None,
        status: str,
    ) -> AIGeneration:
        """
        Reuse an existing version when content hash matches; otherwise insert
        ``version + 1`` as a new immutable row.
        """
        existing = await self.get_by_response_hash(
            feature=feature,
            entity_id=entity_id,
            report_hash=report_hash,
            response_hash=response_hash,
        )
        if existing is not None:
            return existing

        latest = await self.get_latest(
            feature=feature,
            entity_id=entity_id,
            report_hash=report_hash,
        )
        version = (latest.version + 1) if latest is not None else 1
        return await self.create(
            generation_id=generation_id,
            feature=feature,
            entity_type=entity_type,
            entity_id=entity_id,
            audit_id=audit_id,
            provider=provider,
            model=model,
            schema_version=schema_version,
            builder_version=builder_version,
            prompt_version=prompt_version,
            prompt_hash=prompt_hash,
            report_hash=report_hash,
            input_hash=input_hash,
            response_hash=response_hash,
            locale=locale,
            response_json=response_json,
            telemetry_json=telemetry_json,
            diagnostics_json=diagnostics_json,
            status=status,
            version=version,
        )

    async def get_version(
        self,
        *,
        feature: AIFeature | str,
        entity_id: str,
        report_hash: str | None,
        version: int,
    ) -> AIGeneration | None:
        """Load one immutable version for feature + entity + report_hash."""
        rh = report_hash or ""
        result = await self._session.execute(
            select(AIGeneration).where(
                AIGeneration.feature == str(feature),
                AIGeneration.entity_id == entity_id,
                AIGeneration.report_hash == rh,
                AIGeneration.version == version,
            )
        )
        return result.scalar_one_or_none()

    async def get_versions(
        self,
        *,
        feature: AIFeature | str,
        entity_id: str,
        report_hash: str | None,
    ) -> list[AIGeneration]:
        """Alias of ``list_versions`` — append-only history, ascending version."""
        return await self.list_versions(
            feature=feature,
            entity_id=entity_id,
            report_hash=report_hash,
        )

    async def latest(
        self,
        *,
        feature: AIFeature | str,
        entity_id: str,
        report_hash: str | None,
    ) -> AIGeneration | None:
        """Alias of ``get_latest`` — highest version for the key (no mutable pointer)."""
        return await self.get_latest(
            feature=feature,
            entity_id=entity_id,
            report_hash=report_hash,
        )

    async def regenerate(
        self,
        *,
        generation_id: UUID | None,
        feature: AIFeature | str,
        entity_type: AIEntityType | str,
        entity_id: str,
        audit_id: UUID | None,
        provider: str,
        model: str,
        schema_version: str,
        builder_version: int,
        prompt_version: str,
        prompt_hash: str | None,
        report_hash: str | None,
        input_hash: str | None,
        response_hash: str,
        locale: str,
        response_json: dict[str, Any],
        telemetry_json: dict[str, Any] | None,
        diagnostics_json: dict[str, Any] | None,
        status: str,
    ) -> AIGeneration:
        """
        Persist a regenerated response.

        Identical ``response_hash`` reuses the existing version; otherwise
        inserts ``version + 1``. Never updates prior rows.
        """
        return await self.create_or_reuse(
            generation_id=generation_id,
            feature=feature,
            entity_type=entity_type,
            entity_id=entity_id,
            audit_id=audit_id,
            provider=provider,
            model=model,
            schema_version=schema_version,
            builder_version=builder_version,
            prompt_version=prompt_version,
            prompt_hash=prompt_hash,
            report_hash=report_hash,
            input_hash=input_hash,
            response_hash=response_hash,
            locale=locale,
            response_json=response_json,
            telemetry_json=telemetry_json,
            diagnostics_json=diagnostics_json,
            status=status,
        )

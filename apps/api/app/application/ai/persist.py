"""Best-effort persistence of grounded AIResponse artifacts."""

from __future__ import annotations

from typing import Any
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.ai.entity_types import AIEntityType, entity_type_for_feature
from app.ai.features import AIFeature
from app.ai.response import AIResponse
from app.application.ai.response_hash import hash_ai_response
from app.core.logging import get_logger
from app.models.ai_generation import AIGeneration
from app.repositories.ai_generation import AIGenerationRepository

logger = get_logger(__name__)


def _status_for(response: AIResponse[Any]) -> str:
    if response.quality is not None and response.quality.cache_hit:
        return "cached"
    if response.provider_metadata.cached:
        return "cached"
    return "success"


class AIGenerationPersister:
    """
    Persist grounded AI responses without affecting generation success.

    Uses a SAVEPOINT so repository failures never poison the request transaction.
    """

    def __init__(self, session: AsyncSession) -> None:
        self._session = session
        self._repo = AIGenerationRepository(session)

    async def persist(
        self,
        response: AIResponse[Any],
        *,
        feature: AIFeature,
        entity_id: str,
        audit_id: UUID | None,
        report_hash: str | None,
        locale: str = "en",
        entity_type: AIEntityType | None = None,
    ) -> AIGeneration | None:
        """
        Store or reuse an immutable generation row.

        Returns the row on success, or ``None`` when persistence fails
        (errors are logged; never raised).
        """
        try:
            async with self._session.begin_nested():
                return await self._persist_inner(
                    response,
                    feature=feature,
                    entity_id=entity_id,
                    audit_id=audit_id,
                    report_hash=report_hash,
                    locale=locale,
                    entity_type=entity_type,
                )
        except Exception:
            logger.exception(
                "ai_generation_persist_failed",
                feature=str(feature),
                entity_id=entity_id,
                audit_id=str(audit_id) if audit_id else None,
                generation_id=(
                    str(response.generation_id) if response.generation_id else None
                ),
            )
            return None

    async def _persist_inner(
        self,
        response: AIResponse[Any],
        *,
        feature: AIFeature,
        entity_id: str,
        audit_id: UUID | None,
        report_hash: str | None,
        locale: str,
        entity_type: AIEntityType | None,
    ) -> AIGeneration:
        quality = response.quality
        meta = response.provider_metadata
        resolved_type = entity_type or entity_type_for_feature(feature)
        response_hash = hash_ai_response(response)

        schema_version = (
            quality.schema_version
            if quality is not None
            else (getattr(response.result, "schema_version", None) or "unknown")
        )
        builder_version = quality.builder_version if quality is not None else 0
        prompt_version = quality.prompt_version if quality is not None else ""
        prompt_hash = quality.prompt_hash if quality is not None else None
        if prompt_hash is None and response.diagnostics is not None:
            prompt_hash = response.diagnostics.prompt_hash

        input_hash = None
        if response.diagnostics is not None:
            input_hash = response.diagnostics.variables_hash

        response_json = response.model_dump(mode="json")
        telemetry_json = (
            response.telemetry.model_dump(mode="json")
            if response.telemetry is not None
            else None
        )
        diagnostics_json = (
            response.diagnostics.model_dump(mode="json")
            if response.diagnostics is not None
            else None
        )

        return await self._repo.regenerate(
            generation_id=response.generation_id,
            feature=feature,
            entity_type=resolved_type,
            entity_id=entity_id,
            audit_id=audit_id,
            provider=meta.provider,
            model=meta.model,
            schema_version=str(schema_version),
            builder_version=int(builder_version),
            prompt_version=str(prompt_version),
            prompt_hash=prompt_hash,
            report_hash=report_hash,
            input_hash=input_hash,
            response_hash=response_hash,
            locale=locale or "en",
            response_json=response_json,
            telemetry_json=telemetry_json,
            diagnostics_json=diagnostics_json,
            status=_status_for(response),
        )

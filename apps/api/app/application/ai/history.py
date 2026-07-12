"""Read-only use cases for persisted AI generation history."""

from __future__ import annotations

from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.application.ai.exceptions import GenerationNotFoundError
from app.application.ai.identity import AIGenerationKey, AIGenerationKeyResolver
from app.models.ai_generation import AIGeneration
from app.repositories.ai_generation import AIGenerationRepository
from app.schemas.ai_generation import GenerationHistoryDTO, GenerationHistoryItem

KeyResolver = Callable[[AIGenerationKeyResolver], Awaitable[AIGenerationKey]]


def _history_dto(key: AIGenerationKey, rows: list[AIGeneration]) -> GenerationHistoryDTO:
    return GenerationHistoryDTO(
        feature=key.feature.value,
        entity_type=key.entity_type.value,
        entity_id=key.entity_id,
        audit_id=key.audit_id,
        report_hash=key.report_hash or "",
        items=[
            GenerationHistoryItem(
                version=row.version,
                created_at=row.created_at,
                provider=row.provider,
                model=row.model,
                prompt_version=row.prompt_version,
                schema_version=row.schema_version,
                generation_id=row.generation_id,
                response_hash=row.response_hash,
            )
            for row in rows
        ],
    )


@dataclass(frozen=True, slots=True)
class GetLatestAIGenerationResult:
    row: AIGeneration
    key: AIGenerationKey


@dataclass(frozen=True, slots=True)
class GetAIGenerationVersionResult:
    row: AIGeneration
    key: AIGenerationKey


@dataclass(frozen=True, slots=True)
class ListAIGenerationVersionsResult:
    history: GenerationHistoryDTO
    key: AIGenerationKey


class GetLatestAIGenerationUseCase:
    def __init__(self, session: AsyncSession, resolve: KeyResolver) -> None:
        self._resolver = AIGenerationKeyResolver(session)
        self._repo = AIGenerationRepository(session)
        self._resolve = resolve

    async def execute(self) -> GetLatestAIGenerationResult:
        key = await self._resolve(self._resolver)
        row = await self._repo.latest(
            feature=key.feature,
            entity_id=key.entity_id,
            report_hash=key.report_hash,
        )
        if row is None:
            raise GenerationNotFoundError(
                "No AI generation found for this entity. Generate or regenerate first.",
            )
        return GetLatestAIGenerationResult(row=row, key=key)


class ListAIGenerationVersionsUseCase:
    def __init__(self, session: AsyncSession, resolve: KeyResolver) -> None:
        self._resolver = AIGenerationKeyResolver(session)
        self._repo = AIGenerationRepository(session)
        self._resolve = resolve

    async def execute(self) -> ListAIGenerationVersionsResult:
        key = await self._resolve(self._resolver)
        rows = await self._repo.get_versions(
            feature=key.feature,
            entity_id=key.entity_id,
            report_hash=key.report_hash,
        )
        return ListAIGenerationVersionsResult(
            history=_history_dto(key, rows),
            key=key,
        )


class GetAIGenerationVersionUseCase:
    def __init__(self, session: AsyncSession, resolve: KeyResolver) -> None:
        self._resolver = AIGenerationKeyResolver(session)
        self._repo = AIGenerationRepository(session)
        self._resolve = resolve

    async def execute(self, version: int) -> GetAIGenerationVersionResult:
        key = await self._resolve(self._resolver)
        row = await self._repo.get_version(
            feature=key.feature,
            entity_id=key.entity_id,
            report_hash=key.report_hash,
            version=version,
        )
        if row is None:
            raise GenerationNotFoundError(
                f"AI generation version {version} was not found for this entity.",
            )
        return GetAIGenerationVersionResult(row=row, key=key)


# Path-ID bound factories (routers pass UUID then call execute).


class _BoundLatest:
    def __init__(self, session: AsyncSession, resolve_fn: Callable[..., Awaitable[AIGenerationKey]]) -> None:
        self._session = session
        self._resolve_fn = resolve_fn

    async def execute(self, resource_id: UUID) -> GetLatestAIGenerationResult:
        async def _resolve(resolver: AIGenerationKeyResolver) -> AIGenerationKey:
            return await self._resolve_fn(resolver, resource_id)

        return await GetLatestAIGenerationUseCase(self._session, _resolve).execute()


class _BoundVersions:
    def __init__(self, session: AsyncSession, resolve_fn: Callable[..., Awaitable[AIGenerationKey]]) -> None:
        self._session = session
        self._resolve_fn = resolve_fn

    async def execute(self, resource_id: UUID) -> ListAIGenerationVersionsResult:
        async def _resolve(resolver: AIGenerationKeyResolver) -> AIGenerationKey:
            return await self._resolve_fn(resolver, resource_id)

        return await ListAIGenerationVersionsUseCase(self._session, _resolve).execute()


class _BoundVersion:
    def __init__(self, session: AsyncSession, resolve_fn: Callable[..., Awaitable[AIGenerationKey]]) -> None:
        self._session = session
        self._resolve_fn = resolve_fn

    async def execute(
        self, resource_id: UUID, version: int
    ) -> GetAIGenerationVersionResult:
        async def _resolve(resolver: AIGenerationKeyResolver) -> AIGenerationKey:
            return await self._resolve_fn(resolver, resource_id)

        return await GetAIGenerationVersionUseCase(self._session, _resolve).execute(
            version
        )


def finding_latest_use_case(session: AsyncSession) -> _BoundLatest:
    return _BoundLatest(
        session, lambda r, rid: r.for_finding(rid)
    )


def finding_versions_use_case(session: AsyncSession) -> _BoundVersions:
    return _BoundVersions(
        session, lambda r, rid: r.for_finding(rid)
    )


def finding_version_use_case(session: AsyncSession) -> _BoundVersion:
    return _BoundVersion(
        session, lambda r, rid: r.for_finding(rid)
    )


def recommendation_latest_use_case(session: AsyncSession) -> _BoundLatest:
    return _BoundLatest(
        session, lambda r, rid: r.for_recommendation(rid)
    )


def recommendation_versions_use_case(session: AsyncSession) -> _BoundVersions:
    return _BoundVersions(
        session, lambda r, rid: r.for_recommendation(rid)
    )


def recommendation_version_use_case(session: AsyncSession) -> _BoundVersion:
    return _BoundVersion(
        session, lambda r, rid: r.for_recommendation(rid)
    )


def quick_win_latest_use_case(session: AsyncSession) -> _BoundLatest:
    return _BoundLatest(
        session, lambda r, rid: r.for_quick_win(rid)
    )


def quick_win_versions_use_case(session: AsyncSession) -> _BoundVersions:
    return _BoundVersions(
        session, lambda r, rid: r.for_quick_win(rid)
    )


def quick_win_version_use_case(session: AsyncSession) -> _BoundVersion:
    return _BoundVersion(
        session, lambda r, rid: r.for_quick_win(rid)
    )


def executive_latest_use_case(session: AsyncSession) -> _BoundLatest:
    return _BoundLatest(
        session, lambda r, rid: r.for_executive_summary(rid)
    )


def executive_versions_use_case(session: AsyncSession) -> _BoundVersions:
    return _BoundVersions(
        session, lambda r, rid: r.for_executive_summary(rid)
    )


def executive_version_use_case(session: AsyncSession) -> _BoundVersion:
    return _BoundVersion(
        session, lambda r, rid: r.for_executive_summary(rid)
    )


def business_latest_use_case(session: AsyncSession) -> _BoundLatest:
    return _BoundLatest(
        session, lambda r, rid: r.for_business_summary(rid)
    )


def business_versions_use_case(session: AsyncSession) -> _BoundVersions:
    return _BoundVersions(
        session, lambda r, rid: r.for_business_summary(rid)
    )


def business_version_use_case(session: AsyncSession) -> _BoundVersion:
    return _BoundVersion(
        session, lambda r, rid: r.for_business_summary(rid)
    )

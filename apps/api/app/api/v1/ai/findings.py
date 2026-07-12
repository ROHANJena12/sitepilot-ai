"""Finding AI explanation endpoints."""

from __future__ import annotations

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, BackgroundTasks, Depends, Request

from app.ai.features import AIFeature
from app.ai.jobs.queue import QueuePort
from app.ai.response import AIResponse
from app.ai.schemas import FindingExplanation
from app.ai.service import AIService
from app.api.v1.ai.enqueue import enqueue_generation
from app.api.v1.ai.errors import AI_ERROR_RESPONSES, raise_http_from_ai_orchestration
from app.api.v1.ai.response import ai_json_response, stored_ai_json_response
from app.application.ai.findings.generate_finding_explanation import (
    GenerateFindingExplanationUseCase,
)
from app.application.ai.findings.regenerate_finding_explanation import (
    RegenerateFindingExplanationUseCase,
)
from app.application.ai.history import (
    finding_latest_use_case,
    finding_version_use_case,
    finding_versions_use_case,
)
from app.dependencies.ai import get_ai_service
from app.dependencies.ai_jobs import get_job_queue
from app.dependencies.db import DbSession
from app.schemas.ai_generation import GenerationHistoryDTO
from app.schemas.ai_job import GenerationJobAcceptedDTO

router = APIRouter(prefix="/findings", tags=["AI"])

_FINDING_EXAMPLE = {
    "generation_id": "6f2c8a1e-1111-2222-3333-abcdef012345",
    "result": {
        "finding_id": "seo.viewport.missing",
        "title": "Missing viewport",
        "explanation": "No viewport meta tag was detected in the document head.",
        "why_it_matters": "Search engines may treat the page poorly on mobile.",
        "suggested_fix_summary": "Add a responsive viewport meta tag.",
        "severity": "high",
        "category": "seo",
    },
    "quality": {
        "grounded": True,
        "validation_passed": True,
        "cache_hit": False,
        "provider": "openai",
        "model": "gpt-5.5",
        "prompt_version": "v1",
        "builder_version": 1,
        "schema_version": "ai.finding_explanation.v3",
        "feature": "finding",
    },
    "provider_metadata": {
        "provider": "openai",
        "model": "gpt-5.5",
        "cached": False,
        "retry_count": 0,
    },
    "telemetry": None,
    "diagnostics": None,
    "session_id": "11111111-2222-3333-4444-555555555555",
    "generated_at": "2026-07-12T02:30:00Z",
}


def get_finding_explanation_use_case(
    session: DbSession,
    ai_service: Annotated[AIService, Depends(get_ai_service)],
) -> GenerateFindingExplanationUseCase:
    return GenerateFindingExplanationUseCase(session, ai_service)


@router.post(
    "/{finding_id}/ai/generate",
    response_model=GenerationJobAcceptedDTO,
    status_code=202,
    operation_id="generateFindingAiExplanationAsync",
    summary="Queue finding explanation job",
    description=(
        "Enqueue async finding explanation. Returns `202` with `job_id` immediately. "
        "Poll `GET /api/v1/jobs/{job_id}` then `GET /api/v1/jobs/{job_id}/result`."
    ),
    responses={
        202: {"description": "Job accepted.", "model": GenerationJobAcceptedDTO},
        **AI_ERROR_RESPONSES,
    },
)
async def generate_finding_explanation_async(
    finding_id: UUID,
    request: Request,
    background_tasks: BackgroundTasks,
    session: DbSession,
    queue: Annotated[QueuePort, Depends(get_job_queue)],
    ai_service: Annotated[AIService, Depends(get_ai_service)],
):
    return await enqueue_generation(
        session=session,
        queue=queue,
        ai_service=ai_service,
        request=request,
        background_tasks=background_tasks,
        feature=AIFeature.FINDING,
        resource_id=finding_id,
    )


@router.get(
    "/{finding_id}/ai/explanation",
    response_model=AIResponse[FindingExplanation],
    operation_id="getFindingAiExplanation",
    summary="Explain a finding",
    description=(
        "Generate a grounded natural-language explanation for one persisted finding.\n\n"
        "**Purpose:** Explain why the deterministic finding matters and how to fix it.\n\n"
        "**Input:** `{finding_id}` — UUID of the finding row (`audit_findings.id`), "
        "not the business rule key.\n\n"
        "**Output:** Complete `AIResponse[FindingExplanation]` JSON envelope.\n\n"
        "**Grounding:** Closed-world validation against the finding context; "
        "hallucinated IDs or severity changes are rejected (`422 INVALID_AI_RESPONSE`).\n\n"
        "**Caching:** Served from the in-process AI cache when the content key matches; "
        "no API-level cache logic.\n\n"
        "**Provider:** OpenAI via `AIService` — routers never call the provider directly.\n\n"
        "**Not involved:** Prompt construction, audit pipeline, engines, or persistence."
    ),
    responses={
        200: {
            "description": "Grounded finding explanation.",
            "content": {
                "application/json": {"example": _FINDING_EXAMPLE},
            },
            "headers": {
                "X-Generation-ID": {
                    "description": "Execution id from AIResponse.generation_id",
                    "schema": {"type": "string"},
                },
                "X-AI-Provider": {
                    "description": "Provider name from provider_metadata",
                    "schema": {"type": "string"},
                },
                "X-AI-Model": {
                    "description": "Model id from provider_metadata",
                    "schema": {"type": "string"},
                },
                "X-AI-Cached": {
                    "description": "`true` when provider_metadata.cached",
                    "schema": {"type": "string", "enum": ["true", "false"]},
                },
                "X-AI-Feature": {
                    "description": "AIFeature value (e.g. `finding`)",
                    "schema": {"type": "string"},
                },
            },
        },
        **AI_ERROR_RESPONSES,
    },
)
async def get_finding_explanation(
    finding_id: UUID,
    use_case: Annotated[
        GenerateFindingExplanationUseCase, Depends(get_finding_explanation_use_case)
    ],
):
    try:
        result = await use_case.execute(finding_id)
    except Exception as exc:
        raise_http_from_ai_orchestration(exc)
    return ai_json_response(result.response)


def get_regenerate_finding_use_case(
    session: DbSession,
    ai_service: Annotated[AIService, Depends(get_ai_service)],
) -> RegenerateFindingExplanationUseCase:
    return RegenerateFindingExplanationUseCase(session, ai_service)


@router.post(
    "/{finding_id}/ai/regenerate",
    response_model=AIResponse[FindingExplanation],
    operation_id="regenerateFindingAiExplanation",
    summary="Regenerate finding explanation",
    description=(
        "Re-run finding explanation. Creates a new immutable `ai_generations` version "
        "when content changes; reuses the existing version when `response_hash` matches.\n\n"
        "Does not change deterministic findings or the audit pipeline."
    ),
    responses={200: {"description": "Newest grounded explanation."}, **AI_ERROR_RESPONSES},
)
async def regenerate_finding_explanation(
    finding_id: UUID,
    use_case: Annotated[
        RegenerateFindingExplanationUseCase, Depends(get_regenerate_finding_use_case)
    ],
):
    try:
        result = await use_case.execute(finding_id)
    except Exception as exc:
        raise_http_from_ai_orchestration(exc)
    return ai_json_response(result.response)


@router.get(
    "/{finding_id}/ai/latest",
    response_model=AIResponse[FindingExplanation],
    operation_id="getFindingAiLatest",
    summary="Latest finding explanation",
    description=(
        "Return the highest-version persisted finding explanation for the current "
        "report hash. Does not call the provider."
    ),
    responses={200: {"description": "Stored AIResponse."}, **AI_ERROR_RESPONSES},
)
async def get_finding_ai_latest(finding_id: UUID, session: DbSession):
    try:
        result = await finding_latest_use_case(session).execute(finding_id)
    except Exception as exc:
        raise_http_from_ai_orchestration(exc)
    return stored_ai_json_response(result.row)


@router.get(
    "/{finding_id}/ai/versions",
    response_model=GenerationHistoryDTO,
    operation_id="listFindingAiVersions",
    summary="Finding explanation version history",
    description="Metadata-only history (no narrative duplication).",
    responses={200: {"description": "GenerationHistoryDTO"}, **AI_ERROR_RESPONSES},
)
async def list_finding_ai_versions(finding_id: UUID, session: DbSession):
    try:
        result = await finding_versions_use_case(session).execute(finding_id)
    except Exception as exc:
        raise_http_from_ai_orchestration(exc)
    return result.history


@router.get(
    "/{finding_id}/ai/versions/{version}",
    response_model=AIResponse[FindingExplanation],
    operation_id="getFindingAiVersion",
    summary="Finding explanation by version",
    description="Return one immutable stored AIResponse by version number.",
    responses={200: {"description": "Stored AIResponse."}, **AI_ERROR_RESPONSES},
)
async def get_finding_ai_version(
    finding_id: UUID, version: int, session: DbSession
):
    try:
        result = await finding_version_use_case(session).execute(finding_id, version)
    except Exception as exc:
        raise_http_from_ai_orchestration(exc)
    return stored_ai_json_response(result.row)

"""Recommendation + Quick Win AI explanation endpoints."""

from __future__ import annotations

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, BackgroundTasks, Depends, Request

from app.ai.features import AIFeature
from app.ai.jobs.queue import QueuePort
from app.ai.response import AIResponse
from app.ai.schemas import QuickWinExplanation, RecommendationExplanation
from app.ai.service import AIService
from app.api.v1.ai.enqueue import enqueue_generation
from app.api.v1.ai.errors import AI_ERROR_RESPONSES, raise_http_from_ai_orchestration
from app.api.v1.ai.response import ai_json_response, stored_ai_json_response
from app.application.ai.history import (
    quick_win_latest_use_case,
    quick_win_version_use_case,
    quick_win_versions_use_case,
    recommendation_latest_use_case,
    recommendation_version_use_case,
    recommendation_versions_use_case,
)
from app.application.ai.recommendations.generate_quick_win import (
    GenerateQuickWinExplanationUseCase,
)
from app.application.ai.recommendations.generate_recommendation_explanation import (
    GenerateRecommendationExplanationUseCase,
)
from app.application.ai.recommendations.regenerate_quick_win import (
    RegenerateQuickWinExplanationUseCase,
)
from app.application.ai.recommendations.regenerate_recommendation_explanation import (
    RegenerateRecommendationExplanationUseCase,
)
from app.dependencies.ai import get_ai_service
from app.dependencies.ai_jobs import get_job_queue
from app.dependencies.db import DbSession
from app.schemas.ai_generation import GenerationHistoryDTO
from app.schemas.ai_job import GenerationJobAcceptedDTO

router = APIRouter(prefix="/recommendations", tags=["AI"])

_REC_EXAMPLE = {
    "generation_id": "6f2c8a1e-aaaa-bbbb-cccc-abcdef012345",
    "result": {
        "recommendation_id": "rec.seo.add_viewport",
        "rule_id": "seo.viewport",
        "title": "Add viewport",
        "summary": "Add a viewport meta tag to unlock mobile SEO signals.",
        "why_it_matters": "Improves mobile indexing and usability.",
        "how_to_fix": "Insert a responsive viewport meta tag in <head>.",
        "expected_benefit": "Better mobile search presentation.",
        "technical_details": "Missing viewport meta.",
        "estimated_effort": "Very Low",
    },
    "quality": {
        "grounded": True,
        "validation_passed": True,
        "cache_hit": False,
        "provider": "openai",
        "model": "gpt-5.5",
        "prompt_version": "v1",
        "builder_version": 1,
        "schema_version": "ai.recommendation.v3",
        "feature": "recommendation",
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

_QW_EXAMPLE = {
    **_REC_EXAMPLE,
    "result": {
        "headline": "Fast mobile SEO win",
        "summary": "Viewport is a low-effort high-impact fix.",
        "why_it_matters": "Unblocks mobile usability signals.",
        "expected_benefit": "Better mobile rankings.",
        "implementation_tip": "Add one meta tag in head.",
        "recommendation_id": "rec.seo.add_viewport",
        "rule_id": "seo.viewport",
        "title": "Add viewport",
        "priority": "High",
        "category": "SEO",
        "estimated_effort": "Very Low",
        "estimated_impact": "High",
    },
    "quality": {
        **_REC_EXAMPLE["quality"],
        "schema_version": "ai.quick_win.v3",
        "feature": "quick_win",
    },
}


def get_recommendation_explanation_use_case(
    session: DbSession,
    ai_service: Annotated[AIService, Depends(get_ai_service)],
) -> GenerateRecommendationExplanationUseCase:
    return GenerateRecommendationExplanationUseCase(session, ai_service)


def get_quick_win_explanation_use_case(
    session: DbSession,
    ai_service: Annotated[AIService, Depends(get_ai_service)],
) -> GenerateQuickWinExplanationUseCase:
    return GenerateQuickWinExplanationUseCase(session, ai_service)


@router.post(
    "/{recommendation_id}/ai/generate",
    response_model=GenerationJobAcceptedDTO,
    status_code=202,
    operation_id="generateRecommendationAiExplanationAsync",
    summary="Queue recommendation explanation job",
    description=(
        "Enqueue async recommendation explanation. Returns `202` with `job_id`. "
        "Poll `GET /api/v1/jobs/{job_id}` then `/result`."
    ),
    responses={
        202: {"description": "Job accepted.", "model": GenerationJobAcceptedDTO},
        **AI_ERROR_RESPONSES,
    },
)
async def generate_recommendation_explanation_async(
    recommendation_id: UUID,
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
        feature=AIFeature.RECOMMENDATION,
        resource_id=recommendation_id,
    )


@router.post(
    "/{recommendation_id}/ai/generate-quick-win",
    response_model=GenerationJobAcceptedDTO,
    status_code=202,
    operation_id="generateRecommendationAiQuickWinAsync",
    summary="Queue quick-win explanation job",
    description=(
        "Enqueue async quick-win explanation. Returns `202` with `job_id`. "
        "`409 AI_FEATURE_UNAVAILABLE` when not a quick win."
    ),
    responses={
        202: {"description": "Job accepted.", "model": GenerationJobAcceptedDTO},
        **AI_ERROR_RESPONSES,
    },
)
async def generate_quick_win_explanation_async(
    recommendation_id: UUID,
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
        feature=AIFeature.QUICK_WIN,
        resource_id=recommendation_id,
    )


@router.get(
    "/{recommendation_id}/ai/explanation",
    response_model=AIResponse[RecommendationExplanation],
    operation_id="getRecommendationAiExplanation",
    summary="Explain a recommendation",
    description=(
        "Generate a grounded explanation for one deterministic recommendation.\n\n"
        "**Purpose:** Explain why the recommendation exists and how to implement it.\n\n"
        "**Input:** `{recommendation_id}` — UUID of the recommendation row "
        "(`recommendations.id`), not the business key.\n\n"
        "**Output:** Complete `AIResponse[RecommendationExplanation]`.\n\n"
        "**Grounding:** Identity / effort echoes must match context "
        "(`422 INVALID_AI_RESPONSE` on failure).\n\n"
        "**Caching:** Automatic via `AIService` content keys; no API cache layer.\n\n"
        "**Provider:** OpenAI through `AIService` only.\n\n"
        "**Not involved:** Prompt construction, pipeline, engines, or persistence."
    ),
    responses={
        200: {
            "description": "Grounded recommendation explanation.",
            "content": {"application/json": {"example": _REC_EXAMPLE}},
            "headers": {
                "X-Generation-ID": {"schema": {"type": "string"}},
                "X-AI-Provider": {"schema": {"type": "string"}},
                "X-AI-Model": {"schema": {"type": "string"}},
                "X-AI-Cached": {
                    "schema": {"type": "string", "enum": ["true", "false"]},
                },
                "X-AI-Feature": {"schema": {"type": "string"}},
            },
        },
        **AI_ERROR_RESPONSES,
    },
)
async def get_recommendation_explanation(
    recommendation_id: UUID,
    use_case: Annotated[
        GenerateRecommendationExplanationUseCase,
        Depends(get_recommendation_explanation_use_case),
    ],
):
    try:
        result = await use_case.execute(recommendation_id)
    except Exception as exc:
        raise_http_from_ai_orchestration(exc)
    return ai_json_response(result.response)


@router.get(
    "/{recommendation_id}/ai/quick-win",
    response_model=AIResponse[QuickWinExplanation],
    operation_id="getRecommendationAiQuickWin",
    summary="Explain why a recommendation is a quick win",
    description=(
        "Explain why a deterministic recommendation is considered a quick win.\n\n"
        "**Purpose:** Narrative only — does not invent or re-rank recommendations.\n\n"
        "**Input:** `{recommendation_id}` — persisted recommendation row UUID.\n\n"
        "**Output:** Complete `AIResponse[QuickWinExplanation]`.\n\n"
        "**Grounding:** Priority / effort / impact / category must match context.\n\n"
        "**Caching:** Automatic via `AIService`.\n\n"
        "**Provider:** OpenAI through `AIService` only.\n\n"
        "**Errors:** `409 AI_FEATURE_UNAVAILABLE` when `is_quick_win` is false.\n\n"
        "**Not involved:** Prompt construction, pipeline, engines, or persistence."
    ),
    responses={
        200: {
            "description": "Grounded quick-win explanation.",
            "content": {"application/json": {"example": _QW_EXAMPLE}},
            "headers": {
                "X-Generation-ID": {"schema": {"type": "string"}},
                "X-AI-Provider": {"schema": {"type": "string"}},
                "X-AI-Model": {"schema": {"type": "string"}},
                "X-AI-Cached": {
                    "schema": {"type": "string", "enum": ["true", "false"]},
                },
                "X-AI-Feature": {"schema": {"type": "string"}},
            },
        },
        **AI_ERROR_RESPONSES,
    },
)
async def get_quick_win_explanation(
    recommendation_id: UUID,
    use_case: Annotated[
        GenerateQuickWinExplanationUseCase,
        Depends(get_quick_win_explanation_use_case),
    ],
):
    try:
        result = await use_case.execute(recommendation_id)
    except Exception as exc:
        raise_http_from_ai_orchestration(exc)
    return ai_json_response(result.response)


def get_regenerate_recommendation_use_case(
    session: DbSession,
    ai_service: Annotated[AIService, Depends(get_ai_service)],
) -> RegenerateRecommendationExplanationUseCase:
    return RegenerateRecommendationExplanationUseCase(session, ai_service)


def get_regenerate_quick_win_use_case(
    session: DbSession,
    ai_service: Annotated[AIService, Depends(get_ai_service)],
) -> RegenerateQuickWinExplanationUseCase:
    return RegenerateQuickWinExplanationUseCase(session, ai_service)


@router.post(
    "/{recommendation_id}/ai/regenerate",
    response_model=AIResponse[RecommendationExplanation],
    operation_id="regenerateRecommendationAiExplanation",
    summary="Regenerate recommendation explanation",
    description=(
        "Re-run recommendation explanation. Append-only versioning via "
        "`response_hash`; identical content reuses the existing version."
    ),
    responses={200: {"description": "Newest grounded explanation."}, **AI_ERROR_RESPONSES},
)
async def regenerate_recommendation_explanation(
    recommendation_id: UUID,
    use_case: Annotated[
        RegenerateRecommendationExplanationUseCase,
        Depends(get_regenerate_recommendation_use_case),
    ],
):
    try:
        result = await use_case.execute(recommendation_id)
    except Exception as exc:
        raise_http_from_ai_orchestration(exc)
    return ai_json_response(result.response)


@router.post(
    "/{recommendation_id}/ai/regenerate-quick-win",
    response_model=AIResponse[QuickWinExplanation],
    operation_id="regenerateRecommendationAiQuickWin",
    summary="Regenerate quick-win explanation",
    description=(
        "Re-run quick-win explanation. Append-only versioning; "
        "`409 AI_FEATURE_UNAVAILABLE` when not a quick win."
    ),
    responses={200: {"description": "Newest grounded quick-win."}, **AI_ERROR_RESPONSES},
)
async def regenerate_quick_win_explanation(
    recommendation_id: UUID,
    use_case: Annotated[
        RegenerateQuickWinExplanationUseCase,
        Depends(get_regenerate_quick_win_use_case),
    ],
):
    try:
        result = await use_case.execute(recommendation_id)
    except Exception as exc:
        raise_http_from_ai_orchestration(exc)
    return ai_json_response(result.response)


@router.get(
    "/{recommendation_id}/ai/latest",
    response_model=AIResponse[RecommendationExplanation],
    operation_id="getRecommendationAiLatest",
    summary="Latest recommendation explanation",
    responses={200: {"description": "Stored AIResponse."}, **AI_ERROR_RESPONSES},
)
async def get_recommendation_ai_latest(recommendation_id: UUID, session: DbSession):
    try:
        result = await recommendation_latest_use_case(session).execute(recommendation_id)
    except Exception as exc:
        raise_http_from_ai_orchestration(exc)
    return stored_ai_json_response(result.row)


@router.get(
    "/{recommendation_id}/ai/versions",
    response_model=GenerationHistoryDTO,
    operation_id="listRecommendationAiVersions",
    summary="Recommendation explanation version history",
    responses={200: {"description": "GenerationHistoryDTO"}, **AI_ERROR_RESPONSES},
)
async def list_recommendation_ai_versions(
    recommendation_id: UUID, session: DbSession
):
    try:
        result = await recommendation_versions_use_case(session).execute(
            recommendation_id
        )
    except Exception as exc:
        raise_http_from_ai_orchestration(exc)
    return result.history


@router.get(
    "/{recommendation_id}/ai/versions/{version}",
    response_model=AIResponse[RecommendationExplanation],
    operation_id="getRecommendationAiVersion",
    summary="Recommendation explanation by version",
    responses={200: {"description": "Stored AIResponse."}, **AI_ERROR_RESPONSES},
)
async def get_recommendation_ai_version(
    recommendation_id: UUID, version: int, session: DbSession
):
    try:
        result = await recommendation_version_use_case(session).execute(
            recommendation_id, version
        )
    except Exception as exc:
        raise_http_from_ai_orchestration(exc)
    return stored_ai_json_response(result.row)


@router.get(
    "/{recommendation_id}/ai/quick-win/latest",
    response_model=AIResponse[QuickWinExplanation],
    operation_id="getRecommendationAiQuickWinLatest",
    summary="Latest quick-win explanation",
    responses={200: {"description": "Stored AIResponse."}, **AI_ERROR_RESPONSES},
)
async def get_quick_win_ai_latest(recommendation_id: UUID, session: DbSession):
    try:
        result = await quick_win_latest_use_case(session).execute(recommendation_id)
    except Exception as exc:
        raise_http_from_ai_orchestration(exc)
    return stored_ai_json_response(result.row)


@router.get(
    "/{recommendation_id}/ai/quick-win/versions",
    response_model=GenerationHistoryDTO,
    operation_id="listRecommendationAiQuickWinVersions",
    summary="Quick-win explanation version history",
    responses={200: {"description": "GenerationHistoryDTO"}, **AI_ERROR_RESPONSES},
)
async def list_quick_win_ai_versions(recommendation_id: UUID, session: DbSession):
    try:
        result = await quick_win_versions_use_case(session).execute(recommendation_id)
    except Exception as exc:
        raise_http_from_ai_orchestration(exc)
    return result.history


@router.get(
    "/{recommendation_id}/ai/quick-win/versions/{version}",
    response_model=AIResponse[QuickWinExplanation],
    operation_id="getRecommendationAiQuickWinVersion",
    summary="Quick-win explanation by version",
    responses={200: {"description": "Stored AIResponse."}, **AI_ERROR_RESPONSES},
)
async def get_quick_win_ai_version(
    recommendation_id: UUID, version: int, session: DbSession
):
    try:
        result = await quick_win_version_use_case(session).execute(
            recommendation_id, version
        )
    except Exception as exc:
        raise_http_from_ai_orchestration(exc)
    return stored_ai_json_response(result.row)

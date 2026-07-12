"""Audit-level AI summary endpoints (executive + business)."""

from __future__ import annotations

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, BackgroundTasks, Depends, Request

from app.ai.features import AIFeature
from app.ai.jobs.queue import QueuePort
from app.ai.response import AIResponse
from app.ai.schemas import BusinessSummary, ExecutiveSummary
from app.ai.service import AIService
from app.api.v1.ai.enqueue import enqueue_generation
from app.api.v1.ai.errors import AI_ERROR_RESPONSES, raise_http_from_ai_orchestration
from app.api.v1.ai.response import ai_json_response, stored_ai_json_response
from app.application.ai.history import (
    business_latest_use_case,
    business_version_use_case,
    business_versions_use_case,
    executive_latest_use_case,
    executive_version_use_case,
    executive_versions_use_case,
)
from app.application.ai.reports.generate_business_summary import (
    GenerateBusinessSummaryUseCase,
)
from app.application.ai.reports.generate_executive_summary import (
    GenerateExecutiveSummaryUseCase,
)
from app.application.ai.reports.regenerate_business_summary import (
    RegenerateBusinessSummaryUseCase,
)
from app.application.ai.reports.regenerate_executive_summary import (
    RegenerateExecutiveSummaryUseCase,
)
from app.dependencies.ai import get_ai_service
from app.dependencies.ai_jobs import get_job_queue
from app.dependencies.db import DbSession
from app.schemas.ai_generation import GenerationHistoryDTO
from app.schemas.ai_job import GenerationJobAcceptedDTO

router = APIRouter(prefix="/audits", tags=["AI"])

_EXEC_EXAMPLE = {
    "generation_id": "6f2c8a1e-eeee-ffff-0000-abcdef012345",
    "result": {
        "headline": "Solid foundation with a few high-impact gaps",
        "summary": "Overall score is strong; fix viewport next.",
        "key_risks": ["Missing viewport"],
        "priority_actions": ["Add viewport meta"],
        "positive_observations": ["Strong security baseline"],
        "overall_score": 90,
    },
    "quality": {
        "grounded": True,
        "validation_passed": True,
        "cache_hit": False,
        "provider": "openai",
        "model": "gpt-5.5",
        "prompt_version": "v1",
        "builder_version": 1,
        "schema_version": "ai.executive_summary.v3",
        "feature": "executive_summary",
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

_BIZ_EXAMPLE = {
    **_EXEC_EXAMPLE,
    "result": {
        "headline": "Business impact is contained",
        "summary": "One mobile SEO gap affects discovery.",
        "key_risks": ["Mobile discovery"],
        "priority_actions": ["Ship viewport fix"],
        "positive_observations": ["Clear value proposition"],
        "customer_impact": "Some mobile visitors may bounce.",
        "business_opportunities": ["Improve organic CTR"],
        "overall_score": 90,
    },
    "quality": {
        **_EXEC_EXAMPLE["quality"],
        "schema_version": "ai.business_summary.v3",
        "feature": "business_summary",
    },
}


def get_executive_summary_use_case(
    session: DbSession,
    ai_service: Annotated[AIService, Depends(get_ai_service)],
) -> GenerateExecutiveSummaryUseCase:
    return GenerateExecutiveSummaryUseCase(session, ai_service)


def get_business_summary_use_case(
    session: DbSession,
    ai_service: Annotated[AIService, Depends(get_ai_service)],
) -> GenerateBusinessSummaryUseCase:
    return GenerateBusinessSummaryUseCase(session, ai_service)


@router.post(
    "/{audit_id}/ai/generate-executive-summary",
    response_model=GenerationJobAcceptedDTO,
    status_code=202,
    operation_id="generateAuditAiExecutiveSummaryAsync",
    summary="Queue executive summary job",
    description=(
        "Enqueue async executive summary. Returns `202` with `job_id`. "
        "Poll `GET /api/v1/jobs/{job_id}` then `/result`."
    ),
    responses={
        202: {"description": "Job accepted.", "model": GenerationJobAcceptedDTO},
        **AI_ERROR_RESPONSES,
    },
)
async def generate_executive_summary_async(
    audit_id: UUID,
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
        feature=AIFeature.EXECUTIVE_SUMMARY,
        resource_id=audit_id,
    )


@router.post(
    "/{audit_id}/ai/generate-business-summary",
    response_model=GenerationJobAcceptedDTO,
    status_code=202,
    operation_id="generateAuditAiBusinessSummaryAsync",
    summary="Queue business summary job",
    description=(
        "Enqueue async business summary. Returns `202` with `job_id`. "
        "Poll `GET /api/v1/jobs/{job_id}` then `/result`."
    ),
    responses={
        202: {"description": "Job accepted.", "model": GenerationJobAcceptedDTO},
        **AI_ERROR_RESPONSES,
    },
)
async def generate_business_summary_async(
    audit_id: UUID,
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
        feature=AIFeature.BUSINESS_SUMMARY,
        resource_id=audit_id,
    )


@router.get(
    "/{audit_id}/ai/executive-summary",
    response_model=AIResponse[ExecutiveSummary],
    operation_id="getAuditAiExecutiveSummary",
    summary="Generate executive summary",
    description=(
        "Generate a grounded executive narrative for a completed audit report.\n\n"
        "**Purpose:** Concise leadership-ready explanation of the deterministic report.\n\n"
        "**Input:** `{audit_id}` — audit run UUID.\n\n"
        "**Output:** Complete `AIResponse[ExecutiveSummary]`.\n\n"
        "**Grounding:** Scores / counts must match report context "
        "(`422 INVALID_AI_RESPONSE` on failure).\n\n"
        "**Caching:** Automatic via `AIService` (entity id = audit_id).\n\n"
        "**Provider:** OpenAI through `AIService` only.\n\n"
        "**Not involved:** Prompt construction, pipeline, engines, or persistence."
    ),
    responses={
        200: {
            "description": "Grounded executive summary.",
            "content": {"application/json": {"example": _EXEC_EXAMPLE}},
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
async def get_executive_summary(
    audit_id: UUID,
    use_case: Annotated[
        GenerateExecutiveSummaryUseCase, Depends(get_executive_summary_use_case)
    ],
):
    try:
        result = await use_case.execute(audit_id)
    except Exception as exc:
        raise_http_from_ai_orchestration(exc)
    return ai_json_response(result.response)


@router.get(
    "/{audit_id}/ai/business-summary",
    response_model=AIResponse[BusinessSummary],
    operation_id="getAuditAiBusinessSummary",
    summary="Generate business summary",
    description=(
        "Generate a grounded business narrative for a completed audit report.\n\n"
        "**Purpose:** Explain business impact from deterministic analysis only.\n\n"
        "**Input:** `{audit_id}` — audit run UUID.\n\n"
        "**Output:** Complete `AIResponse[BusinessSummary]`.\n\n"
        "**Grounding:** Closed-world validation against report context.\n\n"
        "**Caching:** Automatic via `AIService` (entity id = audit_id).\n\n"
        "**Provider:** OpenAI through `AIService` only.\n\n"
        "**Not involved:** Prompt construction, pipeline, engines, or persistence."
    ),
    responses={
        200: {
            "description": "Grounded business summary.",
            "content": {"application/json": {"example": _BIZ_EXAMPLE}},
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
async def get_business_summary(
    audit_id: UUID,
    use_case: Annotated[
        GenerateBusinessSummaryUseCase, Depends(get_business_summary_use_case)
    ],
):
    try:
        result = await use_case.execute(audit_id)
    except Exception as exc:
        raise_http_from_ai_orchestration(exc)
    return ai_json_response(result.response)


def get_regenerate_executive_use_case(
    session: DbSession,
    ai_service: Annotated[AIService, Depends(get_ai_service)],
) -> RegenerateExecutiveSummaryUseCase:
    return RegenerateExecutiveSummaryUseCase(session, ai_service)


def get_regenerate_business_use_case(
    session: DbSession,
    ai_service: Annotated[AIService, Depends(get_ai_service)],
) -> RegenerateBusinessSummaryUseCase:
    return RegenerateBusinessSummaryUseCase(session, ai_service)


@router.post(
    "/{audit_id}/ai/regenerate-executive-summary",
    response_model=AIResponse[ExecutiveSummary],
    operation_id="regenerateAuditAiExecutiveSummary",
    summary="Regenerate executive summary",
    description=(
        "Re-run executive summary. Append-only versioning; identical "
        "`response_hash` reuses the existing version."
    ),
    responses={200: {"description": "Newest grounded summary."}, **AI_ERROR_RESPONSES},
)
async def regenerate_executive_summary(
    audit_id: UUID,
    use_case: Annotated[
        RegenerateExecutiveSummaryUseCase, Depends(get_regenerate_executive_use_case)
    ],
):
    try:
        result = await use_case.execute(audit_id)
    except Exception as exc:
        raise_http_from_ai_orchestration(exc)
    return ai_json_response(result.response)


@router.post(
    "/{audit_id}/ai/regenerate-business-summary",
    response_model=AIResponse[BusinessSummary],
    operation_id="regenerateAuditAiBusinessSummary",
    summary="Regenerate business summary",
    description=(
        "Re-run business summary. Append-only versioning; identical "
        "`response_hash` reuses the existing version."
    ),
    responses={200: {"description": "Newest grounded summary."}, **AI_ERROR_RESPONSES},
)
async def regenerate_business_summary(
    audit_id: UUID,
    use_case: Annotated[
        RegenerateBusinessSummaryUseCase, Depends(get_regenerate_business_use_case)
    ],
):
    try:
        result = await use_case.execute(audit_id)
    except Exception as exc:
        raise_http_from_ai_orchestration(exc)
    return ai_json_response(result.response)


@router.get(
    "/{audit_id}/ai/executive-summary/latest",
    response_model=AIResponse[ExecutiveSummary],
    operation_id="getAuditAiExecutiveSummaryLatest",
    summary="Latest executive summary",
    responses={200: {"description": "Stored AIResponse."}, **AI_ERROR_RESPONSES},
)
async def get_executive_summary_latest(audit_id: UUID, session: DbSession):
    try:
        result = await executive_latest_use_case(session).execute(audit_id)
    except Exception as exc:
        raise_http_from_ai_orchestration(exc)
    return stored_ai_json_response(result.row)


@router.get(
    "/{audit_id}/ai/executive-summary/versions",
    response_model=GenerationHistoryDTO,
    operation_id="listAuditAiExecutiveSummaryVersions",
    summary="Executive summary version history",
    responses={200: {"description": "GenerationHistoryDTO"}, **AI_ERROR_RESPONSES},
)
async def list_executive_summary_versions(audit_id: UUID, session: DbSession):
    try:
        result = await executive_versions_use_case(session).execute(audit_id)
    except Exception as exc:
        raise_http_from_ai_orchestration(exc)
    return result.history


@router.get(
    "/{audit_id}/ai/executive-summary/versions/{version}",
    response_model=AIResponse[ExecutiveSummary],
    operation_id="getAuditAiExecutiveSummaryVersion",
    summary="Executive summary by version",
    responses={200: {"description": "Stored AIResponse."}, **AI_ERROR_RESPONSES},
)
async def get_executive_summary_version(
    audit_id: UUID, version: int, session: DbSession
):
    try:
        result = await executive_version_use_case(session).execute(audit_id, version)
    except Exception as exc:
        raise_http_from_ai_orchestration(exc)
    return stored_ai_json_response(result.row)


@router.get(
    "/{audit_id}/ai/business-summary/latest",
    response_model=AIResponse[BusinessSummary],
    operation_id="getAuditAiBusinessSummaryLatest",
    summary="Latest business summary",
    responses={200: {"description": "Stored AIResponse."}, **AI_ERROR_RESPONSES},
)
async def get_business_summary_latest(audit_id: UUID, session: DbSession):
    try:
        result = await business_latest_use_case(session).execute(audit_id)
    except Exception as exc:
        raise_http_from_ai_orchestration(exc)
    return stored_ai_json_response(result.row)


@router.get(
    "/{audit_id}/ai/business-summary/versions",
    response_model=GenerationHistoryDTO,
    operation_id="listAuditAiBusinessSummaryVersions",
    summary="Business summary version history",
    responses={200: {"description": "GenerationHistoryDTO"}, **AI_ERROR_RESPONSES},
)
async def list_business_summary_versions(audit_id: UUID, session: DbSession):
    try:
        result = await business_versions_use_case(session).execute(audit_id)
    except Exception as exc:
        raise_http_from_ai_orchestration(exc)
    return result.history


@router.get(
    "/{audit_id}/ai/business-summary/versions/{version}",
    response_model=AIResponse[BusinessSummary],
    operation_id="getAuditAiBusinessSummaryVersion",
    summary="Business summary by version",
    responses={200: {"description": "Stored AIResponse."}, **AI_ERROR_RESPONSES},
)
async def get_business_summary_version(
    audit_id: UUID, version: int, session: DbSession
):
    try:
        result = await business_version_use_case(session).execute(audit_id, version)
    except Exception as exc:
        raise_http_from_ai_orchestration(exc)
    return stored_ai_json_response(result.row)

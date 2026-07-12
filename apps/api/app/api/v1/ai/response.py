"""Convert AIResponse → HTTP JSON with observability headers."""

from __future__ import annotations

from typing import Any, TypeVar

from fastapi.responses import JSONResponse

from app.ai.response import AIResponse

T = TypeVar("T")

HEADER_GENERATION_ID = "X-Generation-ID"
HEADER_AI_PROVIDER = "X-AI-Provider"
HEADER_AI_MODEL = "X-AI-Model"
HEADER_AI_CACHED = "X-AI-Cached"
HEADER_AI_FEATURE = "X-AI-Feature"


def ai_response_headers(response: AIResponse[Any]) -> dict[str, str]:
    """
    Expose existing AIResponse metadata as HTTP headers.

    Values are copied from the response — nothing is recomputed.
    """
    meta = response.provider_metadata
    feature = None
    if response.quality is not None and response.quality.feature is not None:
        feature = response.quality.feature
    elif meta.feature is not None:
        feature = meta.feature

    return {
        HEADER_GENERATION_ID: (
            str(response.generation_id) if response.generation_id is not None else ""
        ),
        HEADER_AI_PROVIDER: meta.provider,
        HEADER_AI_MODEL: meta.model,
        HEADER_AI_CACHED: "true" if meta.cached else "false",
        HEADER_AI_FEATURE: str(feature) if feature is not None else "",
    }


def ai_json_response(response: AIResponse[T]) -> JSONResponse:
    """
    Serialize ``AIResponse[T]`` to JSON with observability headers.

    Body shape is identical to ``response.model_dump(mode="json")`` —
    the same payload FastAPI would emit for ``response_model=AIResponse[T]``.
    """
    return JSONResponse(
        content=response.model_dump(mode="json"),
        headers=ai_response_headers(response),
    )


def stored_ai_json_response(row: Any) -> JSONResponse:
    """
    Return a persisted ``response_json`` as HTTP JSON with observability headers.

    Body is the stored AIResponse dump — not reconstructed through AIService.
    """
    body = dict(row.response_json or {})
    cached = False
    quality = body.get("quality")
    if isinstance(quality, dict):
        cached = bool(quality.get("cache_hit"))
    meta = body.get("provider_metadata")
    if isinstance(meta, dict) and meta.get("cached"):
        cached = True
    feature = ""
    if isinstance(quality, dict) and quality.get("feature"):
        feature = str(quality["feature"])
    elif row.feature:
        feature = str(row.feature)
    return JSONResponse(
        content=body,
        headers={
            HEADER_GENERATION_ID: (
                str(row.generation_id) if row.generation_id is not None else ""
            ),
            HEADER_AI_PROVIDER: row.provider,
            HEADER_AI_MODEL: row.model,
            HEADER_AI_CACHED: "true" if cached else "false",
            HEADER_AI_FEATURE: feature,
        },
    )

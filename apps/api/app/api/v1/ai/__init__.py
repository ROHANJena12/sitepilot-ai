"""AI HTTP routers — feature-split modules (Sprint 23.1)."""

from __future__ import annotations

from app.api.v1.ai.findings import router as findings_ai_router
from app.api.v1.ai.jobs import router as jobs_ai_router
from app.api.v1.ai.recommendations import router as recommendations_ai_router
from app.api.v1.ai.reports import router as audits_ai_router

__all__ = [
    "audits_ai_router",
    "findings_ai_router",
    "jobs_ai_router",
    "recommendations_ai_router",
]

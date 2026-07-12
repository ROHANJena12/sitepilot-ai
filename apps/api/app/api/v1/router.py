"""API v1 router aggregate."""

from __future__ import annotations

from fastapi import APIRouter

from app.api.health import router as health_router
from app.api.v1.ai import (
    audits_ai_router,
    findings_ai_router,
    jobs_ai_router,
    recommendations_ai_router,
)
from app.api.v1.audits import router as audits_router
from app.api.v1.export import router as export_router
from app.api.v1.share import audits_share_router, share_router
from app.api.v1.websites import router as websites_router

router = APIRouter()
router.include_router(health_router)
router.include_router(websites_router)
router.include_router(audits_router)
router.include_router(export_router)
router.include_router(audits_share_router)
router.include_router(share_router)
router.include_router(audits_ai_router)
router.include_router(findings_ai_router)
router.include_router(recommendations_ai_router)
router.include_router(jobs_ai_router)

"""AI context mappers — Domain DTO → Feature Context → AIContext (no ORM)."""

from __future__ import annotations

from app.ai.mappers.base import AIContextMapper
from app.ai.mappers.business import (
    BusinessSummaryMapInput,
    BusinessSummaryMapper,
    build_business_summary_context,
    report_to_business_ai_context,
)
from app.ai.mappers.executive import (
    ExecutiveSummaryMapInput,
    ExecutiveSummaryMapper,
    ReportLike,
    build_executive_summary_context,
    report_to_executive_ai_context,
)
from app.ai.mappers.finding import (
    FindingLike,
    FindingMapInput,
    FindingMapper,
    finding_to_ai_context,
)
from app.ai.mappers.quick_win import (
    QuickWinMapInput,
    QuickWinMapper,
    build_quick_win_context,
    recommendation_to_quick_win_ai_context,
)
from app.ai.mappers.recommendation import (
    RecommendationLike,
    RecommendationMapInput,
    RecommendationMapper,
    build_recommendation_ai_context,
    build_recommendation_explanation_context,
    recommendation_to_ai_context,
)

__all__ = [
    "AIContextMapper",
    "BusinessSummaryMapInput",
    "BusinessSummaryMapper",
    "ExecutiveSummaryMapInput",
    "ExecutiveSummaryMapper",
    "FindingLike",
    "FindingMapInput",
    "FindingMapper",
    "QuickWinMapInput",
    "QuickWinMapper",
    "RecommendationLike",
    "RecommendationMapInput",
    "RecommendationMapper",
    "ReportLike",
    "build_business_summary_context",
    "build_executive_summary_context",
    "build_quick_win_context",
    "build_recommendation_ai_context",
    "build_recommendation_explanation_context",
    "finding_to_ai_context",
    "recommendation_to_ai_context",
    "recommendation_to_quick_win_ai_context",
    "report_to_business_ai_context",
    "report_to_executive_ai_context",
]

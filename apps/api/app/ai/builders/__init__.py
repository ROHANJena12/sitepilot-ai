"""Prompt builders — map AIContext to prompt strings (no ORM)."""

from __future__ import annotations

from app.ai.builders.base import BuiltPrompt, PromptBuilder, prompt_template_hash
from app.ai.builders.business_summary_builder import BusinessSummaryBuilder
from app.ai.builders.executive_summary_builder import ExecutiveSummaryBuilder
from app.ai.builders.finding_builder import FindingExplanationBuilder
from app.ai.builders.quick_win_builder import QuickWinBuilder
from app.ai.builders.recommendation_builder import RecommendationExplanationBuilder

__all__ = [
    "BuiltPrompt",
    "BusinessSummaryBuilder",
    "ExecutiveSummaryBuilder",
    "FindingExplanationBuilder",
    "PromptBuilder",
    "QuickWinBuilder",
    "RecommendationExplanationBuilder",
    "prompt_template_hash",
]

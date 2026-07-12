"""Pure Recommendation & Priority analysis entrypoint."""

from __future__ import annotations

from app.engines.recommendation.rules import build_recommendations
from app.engines.recommendation.schemas import RecommendationAnalysis
from app.engines.recommendation.validators import RecommendationInput


def analyze_recommendations(inp: RecommendationInput) -> RecommendationAnalysis:
    """Transform findings + health into prioritized recommendations."""
    return build_recommendations(inp)

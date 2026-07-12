"""Recommendation & Priority Engine — deterministic template-based recommendations."""

from app.engines.recommendation.adapter import RecommendationEngine
from app.engines.recommendation.constants import ENGINE_NAME, SCHEMA_VERSION
from app.engines.recommendation.schemas import Recommendation, RecommendationAnalysis

__all__ = [
    "ENGINE_NAME",
    "SCHEMA_VERSION",
    "Recommendation",
    "RecommendationAnalysis",
    "RecommendationEngine",
]

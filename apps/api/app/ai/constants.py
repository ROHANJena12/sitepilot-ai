"""AI foundation constants."""

from __future__ import annotations

from typing import Final

from app.ai.providers.provider_enum import AIProvider

PACKAGE_NAME: Final[str] = "ai"
SCHEMA_NAMESPACE: Final[str] = "ai"

# Known prompt template ids (filename stem without .md).
PROMPT_IDS: Final[tuple[str, ...]] = (
    "finding_explanation",
    "recommendation",
    "executive_summary",
    "business_summary",
    "quick_win",
)

# Supported Mustache-style placeholders across all prompts.
KNOWN_PLACEHOLDERS: Final[frozenset[str]] = frozenset(
    {
        "finding",
        "recommendation",
        "severity",
        "health_score",
        "category",
        "business_impact",
        "website",
        "summary",
        "title",
        "description",
        "evidence",
        "priority",
        "estimated_effort",
        "estimated_impact",
        "overall_score",
        "grade",
        "statistics",
        "quick_wins",
        "critical_issues",
        "report_hash",
        "category_scores",
        "top_priorities",
        "counts",
        "business_impacts",
        "business_findings",
        "critical_business_issues",
        "highest_priorities",
        "recommendation_titles",
        "quick_win_titles",
        "customer_impact",
        "business_risk",
        "business_opportunities",
        "priority_actions",
        "positive_observations",
    }
)

DEFAULT_PROVIDER: Final[AIProvider] = AIProvider.GEMINI
DEFAULT_MODEL: Final[str] = "gemini-3.1-flash-lite"
DEFAULT_OPENAI_MODEL: Final[str] = "gpt-5.5"
DEFAULT_TEMPERATURE: Final[float] = 0.1
DEFAULT_MAX_TOKENS: Final[int] = 1024
DEFAULT_TIMEOUT_SECONDS: Final[float] = 20.0
DEFAULT_RETRY_COUNT: Final[int] = 2

PROVIDER_OPENAI: Final[str] = AIProvider.OPENAI.value
PROVIDER_OPENROUTER: Final[str] = AIProvider.OPENROUTER.value
PROVIDER_ANTHROPIC: Final[str] = AIProvider.ANTHROPIC.value
PROVIDER_GEMINI: Final[str] = AIProvider.GEMINI.value
PROVIDER_OLLAMA: Final[str] = AIProvider.OLLAMA.value

DEFAULT_OPENROUTER_MODEL: Final[str] = "openai/gpt-oss-20b:free"
DEFAULT_OPENROUTER_BASE_URL: Final[str] = "https://openrouter.ai/api/v1"

SUPPORTED_PROVIDERS: Final[tuple[str, ...]] = tuple(p.value for p in AIProvider)

PROMPT_VERSION_HEADER: Final[str] = "Prompt-Version"

# Output schema contract versions (independent of prompt template versions).
SCHEMA_VERSION_FINDING_EXPLANATION: Final[str] = "ai.finding_explanation.v2"
SCHEMA_VERSION_RECOMMENDATION: Final[str] = "ai.recommendation.v3"
SCHEMA_VERSION_EXECUTIVE_SUMMARY: Final[str] = "ai.executive_summary.v3"
SCHEMA_VERSION_BUSINESS_SUMMARY: Final[str] = "ai.business_summary.v3"
SCHEMA_VERSION_QUICK_WIN: Final[str] = "ai.quick_win.v3"

SCHEMA_VERSIONS: Final[dict[str, str]] = {
    "finding": SCHEMA_VERSION_FINDING_EXPLANATION,
    "finding_explanation": SCHEMA_VERSION_FINDING_EXPLANATION,
    "recommendation": SCHEMA_VERSION_RECOMMENDATION,
    "executive_summary": SCHEMA_VERSION_EXECUTIVE_SUMMARY,
    "business_summary": SCHEMA_VERSION_BUSINESS_SUMMARY,
    "quick_win": SCHEMA_VERSION_QUICK_WIN,
}

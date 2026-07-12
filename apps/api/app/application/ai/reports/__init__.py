"""Report-level AI summary use cases."""

from app.application.ai.reports.generate_business_summary import (
    GenerateBusinessSummaryResult,
    GenerateBusinessSummaryUseCase,
)
from app.application.ai.reports.generate_executive_summary import (
    GenerateExecutiveSummaryResult,
    GenerateExecutiveSummaryUseCase,
)

__all__ = [
    "GenerateBusinessSummaryResult",
    "GenerateBusinessSummaryUseCase",
    "GenerateExecutiveSummaryResult",
    "GenerateExecutiveSummaryUseCase",
]

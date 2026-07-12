"""Shared list-length limits for AI summary schemas and grounding."""

from __future__ import annotations

from typing import Final

MAX_KEY_RISKS: Final[int] = 5
MAX_PRIORITY_ACTIONS: Final[int] = 5
MAX_POSITIVE_OBSERVATIONS: Final[int] = 5
MAX_BUSINESS_OPPORTUNITIES: Final[int] = 5
MAX_TOP_STRENGTHS: Final[int] = 5  # alias kept for docs / future Quick Win
MAX_SUMMARY_LIST_ITEMS: Final[int] = 5

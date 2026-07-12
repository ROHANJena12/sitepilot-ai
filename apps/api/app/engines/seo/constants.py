"""SEO Intelligence Engine constants and thresholds."""

from __future__ import annotations

from typing import Final

ENGINE_NAME: Final[str] = "seo"
SCHEMA_VERSION: Final[str] = "engine.seo.output.v1"

# Title length (ENGINE_SPEC §9.4)
TITLE_MIN_LEN: Final[int] = 10
TITLE_MAX_LEN: Final[int] = 60

# Meta description length
META_DESC_MIN_LEN: Final[int] = 50
META_DESC_MAX_LEN: Final[int] = 160

# Content thresholds
LOW_WORD_COUNT: Final[int] = 50
EMPTY_WORD_COUNT: Final[int] = 0

# Links
EXCESSIVE_EXTERNAL_LINKS: Final[int] = 50

"""Performance Intelligence Engine constants and thresholds."""

from __future__ import annotations

from typing import Final

ENGINE_NAME: Final[str] = "performance"
SCHEMA_VERSION: Final[str] = "engine.performance.output.v1"

# HTML / DOM
MAX_HTML_SIZE_BYTES: Final[int] = 200_000  # ~200 KiB
MIN_TEXT_TO_MARKUP_RATIO: Final[float] = 0.10
MAX_DOM_NODES: Final[int] = 1_500
MAX_DOM_DEPTH: Final[int] = 32

# Images
MAX_IMAGES: Final[int] = 50

# CSS
MAX_STYLESHEETS: Final[int] = 8
MAX_EXTERNAL_STYLESHEETS: Final[int] = 6
MAX_INLINE_STYLE_CHARS: Final[int] = 8_192

# JavaScript
MAX_SCRIPTS: Final[int] = 15
MAX_INLINE_SCRIPT_BYTES: Final[int] = 10_240

# Fonts
MAX_FONT_FILES: Final[int] = 4

# Network
MAX_EXTERNAL_ASSETS: Final[int] = 40
MAX_THIRD_PARTY_DOMAINS: Final[int] = 8

# Known external font hosts (basic detection)
EXTERNAL_FONT_HOSTS: Final[frozenset[str]] = frozenset(
    {
        "fonts.googleapis.com",
        "fonts.gstatic.com",
        "use.typekit.net",
        "use.fontawesome.com",
        "kit.fontawesome.com",
    }
)

KNOWN_CONTENT_ENCODINGS: Final[frozenset[str]] = frozenset(
    {"gzip", "br", "deflate", "zstd", "compress", "identity"}
)

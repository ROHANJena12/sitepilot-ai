"""Accessibility Intelligence Engine constants."""

from __future__ import annotations

from typing import Final

ENGINE_NAME: Final[str] = "accessibility"
SCHEMA_VERSION: Final[str] = "engine.accessibility.output.v1"

GENERIC_LINK_TEXTS: Final[frozenset[str]] = frozenset(
    {
        "click here",
        "here",
        "read more",
        "learn more",
        "more",
        "link",
        "this link",
        "continue",
        "go",
    }
)

DECORATIVE_SRC_HINTS: Final[tuple[str, ...]] = (
    "spacer",
    "pixel",
    "blank",
    "transparent",
    "1x1",
    "tracking",
)

# Common valid ARIA attribute names (basic allow-list for Sprint 9).
KNOWN_ARIA_ATTRIBUTES: Final[frozenset[str]] = frozenset(
    {
        "aria-activedescendant",
        "aria-atomic",
        "aria-autocomplete",
        "aria-busy",
        "aria-checked",
        "aria-colcount",
        "aria-colindex",
        "aria-colspan",
        "aria-controls",
        "aria-current",
        "aria-describedby",
        "aria-details",
        "aria-disabled",
        "aria-dropeffect",
        "aria-errormessage",
        "aria-expanded",
        "aria-flowto",
        "aria-grabbed",
        "aria-haspopup",
        "aria-hidden",
        "aria-invalid",
        "aria-keyshortcuts",
        "aria-label",
        "aria-labelledby",
        "aria-level",
        "aria-live",
        "aria-modal",
        "aria-multiline",
        "aria-multiselectable",
        "aria-orientation",
        "aria-owns",
        "aria-placeholder",
        "aria-posinset",
        "aria-pressed",
        "aria-readonly",
        "aria-relevant",
        "aria-required",
        "aria-roledescription",
        "aria-rowcount",
        "aria-rowindex",
        "aria-rowspan",
        "aria-selected",
        "aria-setsize",
        "aria-sort",
        "aria-valuemax",
        "aria-valuemin",
        "aria-valuenow",
        "aria-valuetext",
    }
)

# Subset of ARIA roles used for basic validation.
KNOWN_ARIA_ROLES: Final[frozenset[str]] = frozenset(
    {
        "alert",
        "alertdialog",
        "application",
        "article",
        "banner",
        "button",
        "cell",
        "checkbox",
        "columnheader",
        "combobox",
        "complementary",
        "contentinfo",
        "definition",
        "dialog",
        "directory",
        "document",
        "feed",
        "figure",
        "form",
        "grid",
        "gridcell",
        "group",
        "heading",
        "img",
        "link",
        "list",
        "listbox",
        "listitem",
        "log",
        "main",
        "marquee",
        "math",
        "menu",
        "menubar",
        "menuitem",
        "menuitemcheckbox",
        "menuitemradio",
        "navigation",
        "none",
        "note",
        "option",
        "presentation",
        "progressbar",
        "radio",
        "radiogroup",
        "region",
        "row",
        "rowgroup",
        "rowheader",
        "scrollbar",
        "search",
        "searchbox",
        "separator",
        "slider",
        "spinbutton",
        "status",
        "switch",
        "tab",
        "table",
        "tablist",
        "tabpanel",
        "term",
        "textbox",
        "timer",
        "toolbar",
        "tooltip",
        "tree",
        "treegrid",
        "treeitem",
    }
)

# Input types that typically benefit from autocomplete.
AUTOCOMPLETE_EXPECTED_TYPES: Final[frozenset[str]] = frozenset(
    {
        "email",
        "password",
        "tel",
        "text",
        "search",
        "url",
        "name",
    }
)

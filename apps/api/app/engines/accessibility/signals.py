"""
Stdlib HTML signal extraction for accessibility rules.

Consumes ``Document.html`` only — never BeautifulSoup, never a second Parser pass.
Produces an immutable ``AccessibilitySignals`` snapshot for pure rules.
"""

from __future__ import annotations

from collections import Counter
from html.parser import HTMLParser
from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class ScannedButton(BaseModel):
    model_config = ConfigDict(frozen=True)

    text: str = ""
    aria_label: str | None = None
    aria_labelledby: str | None = None
    title: str | None = None
    type: str | None = None
    has_img_child: bool = False


class ScannedInput(BaseModel):
    model_config = ConfigDict(frozen=True)

    tag: str
    type: str | None = None
    name: str | None = None
    id: str | None = None
    placeholder: str | None = None
    autocomplete: str | None = None
    aria_label: str | None = None
    aria_labelledby: str | None = None
    title: str | None = None
    has_label: bool = False


class ScannedTable(BaseModel):
    model_config = ConfigDict(frozen=True)

    has_th: bool = False
    has_caption: bool = False
    has_headers_attr: bool = False


class ScannedVideo(BaseModel):
    model_config = ConfigDict(frozen=True)

    has_track_captions: bool = False
    has_aria_label: bool = False


class ScannedAudio(BaseModel):
    model_config = ConfigDict(frozen=True)

    has_transcript_hint: bool = False
    aria_label: str | None = None


class ScannedClickable(BaseModel):
    model_config = ConfigDict(frozen=True)

    tag: str
    has_onclick: bool = False
    role: str | None = None
    tabindex: str | None = None
    aria_label: str | None = None


class AccessibilitySignals(BaseModel):
    """Extra a11y signals derived once from Document.html (stdlib parser)."""

    model_config = ConfigDict(frozen=True)

    element_ids: tuple[str, ...] = ()
    duplicate_ids: tuple[str, ...] = ()
    aria_attribute_names: tuple[str, ...] = ()
    invalid_aria_attributes: tuple[str, ...] = ()
    invalid_roles: tuple[str, ...] = ()
    buttons: tuple[ScannedButton, ...] = ()
    inputs: tuple[ScannedInput, ...] = ()
    label_fors: tuple[str, ...] = ()
    tables: tuple[ScannedTable, ...] = ()
    videos: tuple[ScannedVideo, ...] = ()
    audio: tuple[ScannedAudio, ...] = ()
    has_main: bool = False
    has_nav: bool = False
    has_header: bool = False
    has_footer: bool = False
    landmark_count: int = 0
    has_skip_link: bool = False
    clickable_non_semantic: tuple[ScannedClickable, ...] = ()
    has_article_or_section: bool = False
    div_count: int = 0
    semantic_count: int = 0


class _A11yHTMLParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.ids: list[str] = []
        self.aria_names: list[str] = []
        self.invalid_aria: list[str] = []
        self.invalid_roles: list[str] = []
        self.buttons: list[ScannedButton] = []
        self.inputs: list[ScannedInput] = []
        self.label_fors: list[str] = []
        self.tables: list[ScannedTable] = []
        self.videos: list[ScannedVideo] = []
        self.audio: list[ScannedAudio] = []
        self.clickables: list[ScannedClickable] = []
        self.has_main = False
        self.has_nav = False
        self.has_header = False
        self.has_footer = False
        self.landmark_count = 0
        self.has_skip_link = False
        self.has_article_or_section = False
        self.div_count = 0
        self.semantic_count = 0
        self._stack: list[dict[str, Any]] = []
        self._anchor_depth = 0
        self._early_anchor_seen = 0
        self._in_label = False
        self._label_text: list[str] = []
        self._button_text: list[str] = []
        self._in_button = False
        self._button_attrs: dict[str, str | None] = {}
        self._button_has_img = False
        self._in_table = False
        self._table_has_th = False
        self._table_has_caption = False
        self._table_has_headers = False
        self._in_video = False
        self._video_has_track = False
        self._video_aria = False
        self._in_audio = False
        self._audio_aria: str | None = None
        self._audio_transcript = False
        self._text_buffer_lower: list[str] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        from app.engines.accessibility.constants import KNOWN_ARIA_ATTRIBUTES, KNOWN_ARIA_ROLES

        ad = {k.lower(): (v or "") for k, v in attrs}
        tag_l = tag.lower()

        el_id = ad.get("id")
        if el_id:
            self.ids.append(el_id)

        for key, value in ad.items():
            if key.startswith("aria-"):
                self.aria_names.append(key)
                if key not in KNOWN_ARIA_ATTRIBUTES:
                    self.invalid_aria.append(key)
            if key == "role" and value:
                role = value.strip().lower()
                if role and role not in KNOWN_ARIA_ROLES:
                    self.invalid_roles.append(role)

        role = (ad.get("role") or "").strip().lower()
        self._count_landmarks(tag_l, role)

        if tag_l == "div":
            self.div_count += 1
        if tag_l in {
            "main",
            "nav",
            "header",
            "footer",
            "aside",
            "article",
            "section",
            "figure",
            "figcaption",
            "ul",
            "ol",
            "li",
            "table",
            "form",
            "button",
            "h1",
            "h2",
            "h3",
            "h4",
            "h5",
            "h6",
        }:
            self.semantic_count += 1
        if tag_l in {"article", "section"}:
            self.has_article_or_section = True

        if tag_l == "a":
            self._anchor_depth += 1
            href = (ad.get("href") or "").strip()
            self._early_anchor_seen += 1
            # Skip link heuristic: early in-document fragment link.
            if self._early_anchor_seen <= 5 and href.startswith("#") and href != "#":
                self._stack.append({"tag": "a", "skip_candidate": True, "text": []})
            else:
                self._stack.append({"tag": "a", "skip_candidate": False, "text": []})

        if tag_l == "label":
            self._in_label = True
            self._label_text = []
            for_id = ad.get("for")
            if for_id:
                self.label_fors.append(for_id)

        if tag_l == "button":
            self._in_button = True
            self._button_text = []
            self._button_has_img = False
            self._button_attrs = {
                "aria_label": ad.get("aria-label") or None,
                "aria_labelledby": ad.get("aria-labelledby") or None,
                "title": ad.get("title") or None,
                "type": ad.get("type") or None,
            }

        if tag_l == "img" and self._in_button:
            self._button_has_img = True

        if tag_l in {"input", "textarea", "select"}:
            itype = (ad.get("type") or ("textarea" if tag_l == "textarea" else "text")).lower()
            if tag_l == "input" and itype in {"hidden", "submit", "button", "reset", "image"}:
                # Non-text controls handled separately for buttons/images.
                if itype in {"submit", "button", "reset", "image"}:
                    self.buttons.append(
                        ScannedButton(
                            text=(ad.get("value") or "").strip(),
                            aria_label=ad.get("aria-label") or None,
                            aria_labelledby=ad.get("aria-labelledby") or None,
                            title=ad.get("title") or None,
                            type=itype,
                            has_img_child=itype == "image",
                        )
                    )
            else:
                self.inputs.append(
                    ScannedInput(
                        tag=tag_l,
                        type=itype if tag_l == "input" else tag_l,
                        name=ad.get("name") or None,
                        id=ad.get("id") or None,
                        placeholder=ad.get("placeholder") or None,
                        autocomplete=ad.get("autocomplete") or None,
                        aria_label=ad.get("aria-label") or None,
                        aria_labelledby=ad.get("aria-labelledby") or None,
                        title=ad.get("title") or None,
                    )
                )

        if tag_l == "table":
            self._in_table = True
            self._table_has_th = False
            self._table_has_caption = False
            self._table_has_headers = False

        if self._in_table and tag_l == "th":
            self._table_has_th = True
        if self._in_table and tag_l == "caption":
            self._table_has_caption = True
        if self._in_table and tag_l == "td" and ad.get("headers"):
            self._table_has_headers = True

        if tag_l == "video":
            self._in_video = True
            self._video_has_track = False
            self._video_aria = bool(ad.get("aria-label") or ad.get("aria-labelledby"))

        if self._in_video and tag_l == "track":
            kind = (ad.get("kind") or "").lower()
            if kind in {"captions", "subtitles"}:
                self._video_has_track = True

        if tag_l == "audio":
            self._in_audio = True
            self._audio_aria = ad.get("aria-label") or None
            self._audio_transcript = False
            described = (ad.get("aria-describedby") or "").lower()
            if "transcript" in described or (
                self._audio_aria and "transcript" in self._audio_aria.lower()
            ):
                self._audio_transcript = True

        # Clickable non-semantic elements
        if tag_l in {"div", "span"} and (
            "onclick" in ad or role in {"button", "link"} or ad.get("tabindex") is not None
        ):
            if "onclick" in ad or role in {"button", "link"}:
                self.clickables.append(
                    ScannedClickable(
                        tag=tag_l,
                        has_onclick="onclick" in ad,
                        role=role or None,
                        tabindex=ad.get("tabindex") or None,
                        aria_label=ad.get("aria-label") or None,
                    )
                )

    def handle_endtag(self, tag: str) -> None:
        tag_l = tag.lower()

        if tag_l == "a" and self._stack and self._stack[-1].get("tag") == "a":
            frame = self._stack.pop()
            text = "".join(frame.get("text", [])).strip().lower()
            if frame.get("skip_candidate") and text and (
                "skip" in text or "jump" in text or "main content" in text
            ):
                self.has_skip_link = True
            self._anchor_depth = max(0, self._anchor_depth - 1)

        if tag_l == "label":
            self._in_label = False

        if tag_l == "button" and self._in_button:
            self.buttons.append(
                ScannedButton(
                    text="".join(self._button_text).strip(),
                    aria_label=self._button_attrs.get("aria_label"),
                    aria_labelledby=self._button_attrs.get("aria_labelledby"),
                    title=self._button_attrs.get("title"),
                    type=self._button_attrs.get("type"),
                    has_img_child=self._button_has_img,
                )
            )
            self._in_button = False

        if tag_l == "table" and self._in_table:
            self.tables.append(
                ScannedTable(
                    has_th=self._table_has_th,
                    has_caption=self._table_has_caption,
                    has_headers_attr=self._table_has_headers,
                )
            )
            self._in_table = False

        if tag_l == "video" and self._in_video:
            self.videos.append(
                ScannedVideo(
                    has_track_captions=self._video_has_track,
                    has_aria_label=self._video_aria,
                )
            )
            self._in_video = False

        if tag_l == "audio" and self._in_audio:
            # Also treat nearby "transcript" text collected while inside audio as hint.
            joined = " ".join(self._text_buffer_lower[-20:])
            if "transcript" in joined:
                self._audio_transcript = True
            self.audio.append(
                ScannedAudio(
                    has_transcript_hint=self._audio_transcript,
                    aria_label=self._audio_aria,
                )
            )
            self._in_audio = False

    def handle_data(self, data: str) -> None:
        text = data.strip()
        if not text:
            return
        lower = text.lower()
        self._text_buffer_lower.append(lower)
        if len(self._text_buffer_lower) > 200:
            self._text_buffer_lower = self._text_buffer_lower[-100:]

        if self._stack and self._stack[-1].get("tag") == "a":
            self._stack[-1]["text"].append(text)
        if self._in_button:
            self._button_text.append(text)
        if self._in_label:
            self._label_text.append(text)

    def _count_landmarks(self, tag: str, role: str) -> None:
        landmark = False
        if tag == "main" or role == "main":
            self.has_main = True
            landmark = True
        if tag == "nav" or role == "navigation":
            self.has_nav = True
            landmark = True
        if tag == "header" or role == "banner":
            self.has_header = True
            landmark = True
        if tag == "footer" or role == "contentinfo":
            self.has_footer = True
            landmark = True
        if role in {"complementary", "search", "form", "region"}:
            landmark = True
        if tag in {"aside"} or role == "complementary":
            landmark = True
        if landmark:
            self.landmark_count += 1


def scan_accessibility_signals(html: str) -> AccessibilitySignals:
    """
    Derive accessibility signals from raw HTML using stdlib ``HTMLParser``.

    This is not a Document rebuild and does not use BeautifulSoup.
    """
    if not html or not html.strip():
        return AccessibilitySignals()

    parser = _A11yHTMLParser()
    try:
        parser.feed(html)
        parser.close()
    except Exception:
        # Soft: malformed markup still yields whatever was collected.
        pass

    id_counts = Counter(parser.ids)
    duplicates = tuple(sorted(i for i, n in id_counts.items() if n > 1))

    # Resolve label association for scanned inputs (for= id + wrapping not fully tracked).
    label_set = set(parser.label_fors)
    inputs = tuple(
        inp.model_copy(update={"has_label": bool(inp.id and inp.id in label_set)})
        for inp in parser.inputs
    )

    return AccessibilitySignals(
        element_ids=tuple(parser.ids),
        duplicate_ids=duplicates,
        aria_attribute_names=tuple(parser.aria_names),
        invalid_aria_attributes=tuple(dict.fromkeys(parser.invalid_aria)),
        invalid_roles=tuple(dict.fromkeys(parser.invalid_roles)),
        buttons=tuple(parser.buttons),
        inputs=inputs,
        label_fors=tuple(parser.label_fors),
        tables=tuple(parser.tables),
        videos=tuple(parser.videos),
        audio=tuple(parser.audio),
        has_main=parser.has_main,
        has_nav=parser.has_nav,
        has_header=parser.has_header,
        has_footer=parser.has_footer,
        landmark_count=parser.landmark_count,
        has_skip_link=parser.has_skip_link,
        clickable_non_semantic=tuple(parser.clickables),
        has_article_or_section=parser.has_article_or_section,
        div_count=parser.div_count,
        semantic_count=parser.semantic_count,
    )

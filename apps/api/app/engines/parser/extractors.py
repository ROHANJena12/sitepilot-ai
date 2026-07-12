"""HTML extractors — all consume a single BeautifulSoup tree (parse once)."""

from __future__ import annotations

import json
import re
from typing import Any
from urllib.parse import urljoin, urlparse

from bs4 import BeautifulSoup, Comment, Doctype, Tag

from app.engines.parser.constants import (
    MAX_COMMENTS,
    MAX_FORMS,
    MAX_HEADING_TEXT,
    MAX_IMAGES,
    MAX_JSON_LD,
    MAX_LINKS,
    MAX_SCRIPTS,
    MAX_SECTION_HTML_CHARS,
    MAX_STYLESHEETS,
)
from app.engines.parser.document import (
    Form,
    FormInput,
    Heading,
    HreflangLink,
    HtmlSection,
    Image,
    Link,
    PageMetadata,
    Script,
    StructuredDataItem,
    Stylesheet,
)

_WS = re.compile(r"\s+")


def collapse_ws(text: str | None) -> str:
    """Collapse whitespace and strip."""
    if not text:
        return ""
    return _WS.sub(" ", text).strip()


def absolute_url(base: str, href: str | None) -> str | None:
    """Resolve ``href`` against ``base``; return None if empty."""
    if href is None:
        return None
    cleaned = href.strip()
    if not cleaned:
        return None
    return urljoin(base, cleaned)


def registrable_host(url: str) -> str | None:
    """Return lowercased hostname for internal/external classification."""
    host = urlparse(url).hostname
    return host.lower().rstrip(".") if host else None


def is_same_site(base_url: str, target_url: str | None) -> bool | None:
    if not target_url:
        return None
    base_host = registrable_host(base_url)
    target_host = registrable_host(target_url)
    if not base_host or not target_host:
        return None
    return base_host == target_host or target_host.endswith(f".{base_host}") or base_host.endswith(
        f".{target_host}"
    )


def extract_doctype(soup: BeautifulSoup) -> str | None:
    for item in soup.contents:
        if isinstance(item, Doctype):
            return f"<!DOCTYPE {item}>"
    return None


def extract_language(soup: BeautifulSoup) -> str | None:
    html = soup.find("html")
    if isinstance(html, Tag):
        lang = html.get("lang") or html.get("xml:lang")
        if lang:
            return str(lang).strip() or None
    return None


def extract_charset(soup: BeautifulSoup, *, header_charset: str | None = None) -> str | None:
    meta_charset = soup.find("meta", attrs={"charset": True})
    if isinstance(meta_charset, Tag) and meta_charset.get("charset"):
        return str(meta_charset["charset"]).strip().lower() or None
    for meta in soup.find_all("meta"):
        if not isinstance(meta, Tag):
            continue
        http_equiv = str(meta.get("http-equiv") or "").lower()
        if http_equiv == "content-type":
            content = str(meta.get("content") or "")
            if "charset=" in content.lower():
                return content.lower().split("charset=", 1)[1].split(";", 1)[0].strip() or None
    return header_charset.lower() if header_charset else None


def extract_meta_content(
    soup: BeautifulSoup,
    *,
    name: str | None = None,
    prop: str | None = None,
) -> str | None:
    """Read ``content`` from a meta tag by name or property (case-insensitive)."""
    if name:
        for meta in soup.find_all("meta"):
            if not isinstance(meta, Tag):
                continue
            if str(meta.get("name") or "").lower() == name.lower() and meta.get("content") is not None:
                return collapse_ws(str(meta.get("content")))
    if prop:
        for meta in soup.find_all("meta"):
            if not isinstance(meta, Tag):
                continue
            if str(meta.get("property") or "").lower() == prop.lower() and meta.get("content") is not None:
                return collapse_ws(str(meta.get("content")))
    return None


def extract_title(soup: BeautifulSoup) -> str | None:
    """Extract ``<title>`` text."""
    title = soup.find("title")
    if isinstance(title, Tag):
        text = collapse_ws(title.get_text())
        return text or None
    return None


def extract_canonical(soup: BeautifulSoup, base_url: str) -> str | None:
    for tag in soup.find_all("link"):
        if not isinstance(tag, Tag):
            continue
        rel = tag.get("rel")
        rels = [r.lower() for r in rel] if isinstance(rel, list) else str(rel or "").lower().split()
        if "canonical" in rels and tag.get("href"):
            return absolute_url(base_url, str(tag.get("href")))
    return None


def extract_favicon(soup: BeautifulSoup, base_url: str) -> str | None:
    for tag in soup.find_all("link"):
        if not isinstance(tag, Tag):
            continue
        rel = tag.get("rel")
        rels = [r.lower() for r in rel] if isinstance(rel, list) else str(rel or "").lower().split()
        if any((r in {"icon", "shortcut", "apple-touch-icon"} or "icon" in r) for r in rels):
            if tag.get("href"):
                return absolute_url(base_url, str(tag.get("href")))
    return None


def extract_metadata(soup: BeautifulSoup, *, base_url: str, title: str | None) -> PageMetadata:
    """Extract common page metadata fields."""
    return PageMetadata(
        title=title,
        description=extract_meta_content(soup, name="description"),
        keywords=extract_meta_content(soup, name="keywords"),
        author=extract_meta_content(soup, name="author"),
        generator=extract_meta_content(soup, name="generator"),
        theme_color=extract_meta_content(soup, name="theme-color"),
        application_name=extract_meta_content(soup, name="application-name"),
        publisher=extract_meta_content(soup, name="publisher"),
        copyright=extract_meta_content(soup, name="copyright"),
        favicon=extract_favicon(soup, base_url),
    )


def extract_open_graph(soup: BeautifulSoup) -> dict[str, str]:
    """Extract all ``og:*`` meta properties."""
    out: dict[str, str] = {}
    for meta in soup.find_all("meta"):
        if not isinstance(meta, Tag):
            continue
        prop = str(meta.get("property") or "").strip()
        if prop.lower().startswith("og:") and meta.get("content") is not None:
            out[prop] = collapse_ws(str(meta.get("content")))
    return out


def extract_twitter_cards(soup: BeautifulSoup) -> dict[str, str]:
    """Extract all ``twitter:*`` meta names."""
    out: dict[str, str] = {}
    for meta in soup.find_all("meta"):
        if not isinstance(meta, Tag):
            continue
        name = str(meta.get("name") or meta.get("property") or "").strip()
        if name.lower().startswith("twitter:") and meta.get("content") is not None:
            out[name] = collapse_ws(str(meta.get("content")))
    return out


def extract_headings(soup: BeautifulSoup) -> tuple[Heading, ...]:
    """Extract ``h1``–``h6`` in document order."""
    items: list[Heading] = []
    order = 0
    for tag in soup.find_all(re.compile(r"^h[1-6]$", re.I)):
        if not isinstance(tag, Tag):
            continue
        level = int(tag.name[1])
        text = collapse_ws(tag.get_text())
        truncated = False
        if len(text) > MAX_HEADING_TEXT:
            text = text[:MAX_HEADING_TEXT]
            truncated = True
        items.append(Heading(level=level, text=text, order=order, truncated=truncated))
        order += 1
    return tuple(items)


def extract_links(soup: BeautifulSoup, base_url: str) -> tuple[Link, ...]:
    """Extract ``<a>`` links (capped)."""
    items: list[Link] = []
    for tag in soup.find_all("a"):
        if not isinstance(tag, Tag):
            continue
        if len(items) >= MAX_LINKS:
            break
        href = tag.get("href")
        href_str = str(href).strip() if href is not None else None
        abs_url = absolute_url(base_url, href_str) if href_str else None
        rel_raw = tag.get("rel")
        if isinstance(rel_raw, list):
            rels = tuple(str(r).lower() for r in rel_raw)
        elif rel_raw:
            rels = tuple(str(rel_raw).lower().split())
        else:
            rels = ()
        lower_href = (href_str or "").lower()
        if lower_href.startswith("mailto:"):
            kind = "mailto"
        elif lower_href.startswith("tel:"):
            kind = "tel"
        elif lower_href.startswith("javascript:"):
            kind = "javascript"
        elif href_str:
            kind = "anchor"
        else:
            kind = "other"
        internal = is_same_site(base_url, abs_url) if kind == "anchor" else None
        items.append(
            Link(
                href=href_str,
                absolute_url=abs_url,
                text=collapse_ws(tag.get_text()),
                title=str(tag.get("title")).strip() if tag.get("title") else None,
                rel=rels,
                target=str(tag.get("target")) if tag.get("target") else None,
                nofollow="nofollow" in rels,
                noopener="noopener" in rels,
                internal=internal,
                kind=kind,  # type: ignore[arg-type]
            )
        )
    return tuple(items)


def extract_images(soup: BeautifulSoup, base_url: str) -> tuple[Image, ...]:
    items: list[Image] = []
    for tag in soup.find_all("img"):
        if not isinstance(tag, Tag):
            continue
        if len(items) >= MAX_IMAGES:
            break
        src = str(tag.get("src")).strip() if tag.get("src") else None
        alt_attr = tag.get("alt")
        alt_missing = alt_attr is None
        alt = None if alt_missing else collapse_ws(str(alt_attr))
        items.append(
            Image(
                src=src,
                absolute_url=absolute_url(base_url, src),
                alt=alt,
                alt_missing=alt_missing,
                title=str(tag.get("title")).strip() if tag.get("title") else None,
                width=str(tag.get("width")) if tag.get("width") is not None else None,
                height=str(tag.get("height")) if tag.get("height") is not None else None,
                loading=str(tag.get("loading")) if tag.get("loading") else None,
                decoding=str(tag.get("decoding")) if tag.get("decoding") else None,
            )
        )
    return tuple(items)


def extract_scripts(soup: BeautifulSoup, base_url: str) -> tuple[Script, ...]:
    items: list[Script] = []
    for tag in soup.find_all("script"):
        if not isinstance(tag, Tag):
            continue
        if len(items) >= MAX_SCRIPTS:
            break
        src = str(tag.get("src")).strip() if tag.get("src") else None
        script_type = str(tag.get("type")).strip() if tag.get("type") else None
        inline = not bool(src)
        inline_text = tag.string or tag.get_text() if inline else None
        items.append(
            Script(
                src=src,
                absolute_url=absolute_url(base_url, src) if src else None,
                type=script_type,
                async_=tag.has_attr("async"),
                defer=tag.has_attr("defer"),
                module=(script_type or "").lower() == "module",
                inline=inline,
                inline_length=len(inline_text) if inline_text is not None else None,
            )
        )
    return tuple(items)


def extract_stylesheets(soup: BeautifulSoup, base_url: str) -> tuple[Stylesheet, ...]:
    items: list[Stylesheet] = []
    for tag in soup.find_all("link"):
        if not isinstance(tag, Tag):
            continue
        rel = tag.get("rel")
        rels = [r.lower() for r in rel] if isinstance(rel, list) else str(rel or "").lower().split()
        if "stylesheet" not in rels:
            continue
        if len(items) >= MAX_STYLESHEETS:
            break
        href = str(tag.get("href")).strip() if tag.get("href") else None
        items.append(
            Stylesheet(
                href=href,
                absolute_url=absolute_url(base_url, href) if href else None,
                media=str(tag.get("media")) if tag.get("media") else None,
                disabled=tag.has_attr("disabled"),
            )
        )
    return tuple(items)


def _input_has_label(soup: BeautifulSoup, tag: Tag) -> bool:
    input_id = tag.get("id")
    if input_id:
        label = soup.find("label", attrs={"for": str(input_id)})
        if label is not None:
            return True
    parent = tag.find_parent("label")
    return parent is not None


def extract_forms(soup: BeautifulSoup, base_url: str) -> tuple[Form, ...]:
    items: list[Form] = []
    for form in soup.find_all("form"):
        if not isinstance(form, Tag):
            continue
        if len(items) >= MAX_FORMS:
            break
        action = str(form.get("action")).strip() if form.get("action") else None
        method = str(form.get("method") or "get").strip().lower() or "get"
        inputs: list[FormInput] = []
        for control in form.find_all(["input", "textarea", "select", "button"]):
            if not isinstance(control, Tag):
                continue
            inputs.append(
                FormInput(
                    type=str(control.get("type") or control.name).lower(),
                    name=str(control.get("name")) if control.get("name") else None,
                    id=str(control.get("id")) if control.get("id") else None,
                    has_label=_input_has_label(soup, control),
                )
            )
        items.append(
            Form(
                method=method,
                action=action,
                absolute_action=absolute_url(base_url, action) if action else None,
                inputs=tuple(inputs),
            )
        )
    return tuple(items)


def extract_structured_data(soup: BeautifulSoup) -> tuple[StructuredDataItem, ...]:
    """Extract JSON-LD, Microdata presence, and basic RDFa detection."""
    items: list[StructuredDataItem] = []

    for tag in soup.find_all("script"):
        if not isinstance(tag, Tag):
            continue
        script_type = str(tag.get("type") or "").lower()
        if "ld+json" not in script_type:
            continue
        if len(items) >= MAX_JSON_LD:
            break
        raw = tag.string or tag.get_text() or ""
        raw = raw.strip()
        data: Any = None
        err: str | None = None
        if raw:
            try:
                data = json.loads(raw)
            except json.JSONDecodeError as exc:
                err = str(exc)
        items.append(
            StructuredDataItem(format="json-ld", raw=raw or None, data=data, parse_error=err)
        )

    # Microdata: itemscope elements (record count-style lightweight entries)
    for tag in soup.find_all(attrs={"itemscope": True}):
        if not isinstance(tag, Tag):
            continue
        if len(items) >= MAX_JSON_LD + 50:
            break
        itemtype = str(tag.get("itemtype") or "")
        items.append(
            StructuredDataItem(
                format="microdata",
                raw=None,
                data={"itemtype": itemtype or None, "tag": tag.name},
            )
        )

    # RDFa basic detection
    for tag in soup.find_all(True):
        if not isinstance(tag, Tag):
            continue
        if any(tag.has_attr(a) for a in ("typeof", "property", "vocab", "resource", "about")):
            if len(items) >= MAX_JSON_LD + 100:
                break
            items.append(
                StructuredDataItem(
                    format="rdfa",
                    raw=None,
                    data={
                        "tag": tag.name,
                        "typeof": tag.get("typeof"),
                        "property": tag.get("property"),
                        "vocab": tag.get("vocab"),
                    },
                )
            )
            # Cap noisy RDFa to first 20 detections
            if sum(1 for i in items if i.format == "rdfa") >= 20:
                break

    return tuple(items)


def extract_hreflang(soup: BeautifulSoup, base_url: str) -> tuple[HreflangLink, ...]:
    items: list[HreflangLink] = []
    for tag in soup.find_all("link"):
        if not isinstance(tag, Tag):
            continue
        hreflang = tag.get("hreflang")
        href = tag.get("href")
        if not hreflang or not href:
            continue
        items.append(
            HreflangLink(
                hreflang=str(hreflang).strip(),
                href=str(href).strip(),
                absolute_url=absolute_url(base_url, str(href)),
            )
        )
    return tuple(items)


def extract_comments(soup: BeautifulSoup) -> tuple[str, ...]:
    comments = [
        collapse_ws(str(c))
        for c in soup.find_all(string=lambda text: isinstance(text, Comment))
    ]
    return tuple(c for c in comments if c)[:MAX_COMMENTS]


def extract_visible_text(soup: BeautifulSoup) -> tuple[str, int]:
    """
    Extract visible text and word count.

    Mutates the soup by removing script/style tags — call after other extractors.
    """
    for tag in soup.find_all(["script", "style", "noscript", "template"]):
        tag.decompose()

    root = soup.body if soup.body is not None else soup
    text = collapse_ws(root.get_text(separator=" "))
    words = [w for w in text.split(" ") if w]
    return text, len(words)


def extract_section(tag: Tag | None) -> HtmlSection:
    if tag is None:
        return HtmlSection(present=False)
    html = str(tag)
    truncated = False
    if len(html) > MAX_SECTION_HTML_CHARS:
        html = html[:MAX_SECTION_HTML_CHARS]
        truncated = True
    return HtmlSection(present=True, html=html, truncated=truncated)


def collect_duplicate_meta_warnings(soup: BeautifulSoup) -> list[str]:
    """Warn when duplicate description/title-like metas appear."""
    warnings: list[str] = []
    titles = soup.find_all("title")
    if len(titles) > 1:
        warnings.append("DUPLICATE_TITLE")
    descriptions = [
        m
        for m in soup.find_all("meta")
        if isinstance(m, Tag) and str(m.get("name") or "").lower() == "description"
    ]
    if len(descriptions) > 1:
        warnings.append("DUPLICATE_META_DESCRIPTION")
    return warnings

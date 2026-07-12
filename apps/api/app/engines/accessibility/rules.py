"""
Pure accessibility rules — Document + AccessibilitySignals → findings.

Each rule is small, independent, reusable, and has no I/O.
Finding IDs follow ``a11y.<area>.<variant>`` (ENGINE_SPEC §12).
"""

from __future__ import annotations

import re
from collections import Counter
from collections.abc import Callable, Sequence

from app.engines.accessibility.constants import (
    AUTOCOMPLETE_EXPECTED_TYPES,
    DECORATIVE_SRC_HINTS,
    GENERIC_LINK_TEXTS,
)
from app.engines.accessibility.findings import AccessibilityCategory
from app.engines.accessibility.signals import AccessibilitySignals
from app.engines.common.findings import Finding, FindingStatus, Severity
from app.engines.parser.document import Document, Image

RuleFn = Callable[[Document, AccessibilitySignals], tuple[Finding, ...]]

_LANG_RE = re.compile(r"^[A-Za-z]{2,3}(-[A-Za-z0-9]{2,8})*$")


def _finding(
    *,
    id: str,
    rule_id: str,
    category: AccessibilityCategory,
    severity: Severity,
    title: str,
    description: str,
    location: str | None = None,
    element: str | None = None,
    evidence: dict | None = None,
    status: FindingStatus = FindingStatus.FAIL,
    wcag: str | None = None,
) -> Finding:
    ev = dict(evidence or {})
    if wcag:
        ev.setdefault("wcag", wcag)
    return Finding(
        id=id,
        rule_id=rule_id,
        category=category.value,
        severity=severity,
        title=title,
        description=description,
        location=location,
        element=element,
        evidence=ev,
        status=status,
    )


def _looks_decorative(image: Image) -> bool:
    src = (image.src or "").lower()
    return any(hint in src for hint in DECORATIVE_SRC_HINTS)


def _accessible_name(*parts: str | None) -> str:
    return " ".join(p.strip() for p in parts if p and p.strip())


# ---------------------------------------------------------------------------
# Images — WCAG 1.1.1
# ---------------------------------------------------------------------------


def check_images(document: Document, _signals: AccessibilitySignals) -> tuple[Finding, ...]:
    findings: list[Finding] = []
    missing: list[dict] = []
    empty_bad: list[dict] = []
    alts = [img.alt for img in document.images if img.alt and img.alt.strip()]

    for idx, image in enumerate(document.images):
        sample = {"index": idx, "src": image.src, "alt": image.alt}
        if image.alt_missing or image.alt is None:
            missing.append(sample)
        elif not str(image.alt).strip() and not _looks_decorative(image):
            # Empty alt is OK for decorative; flag when src does not look decorative
            # and image has a title suggesting it is informative.
            if image.title or (image.width and image.height):
                empty_bad.append(sample)
            elif image.src and not _looks_decorative(image):
                empty_bad.append(sample)

    if missing:
        findings.append(
            _finding(
                id="a11y.images.missing_alt",
                rule_id="images.missing_alt",
                category=AccessibilityCategory.IMAGES,
                severity=Severity.HIGH,
                title="Missing alt attribute",
                description=f"{len(missing)} image(s) are missing an alt attribute.",
                location="body > img",
                element="img",
                evidence={"count": len(missing), "samples": missing[:10]},
                wcag="1.1.1",
            )
        )
    if empty_bad:
        findings.append(
            _finding(
                id="a11y.images.empty_alt_inappropriate",
                rule_id="images.empty_alt_inappropriate",
                category=AccessibilityCategory.IMAGES,
                severity=Severity.MEDIUM,
                title="Empty alt where inappropriate",
                description=(
                    f"{len(empty_bad)} image(s) use empty alt but do not appear decorative."
                ),
                location="body > img",
                element="img",
                evidence={"count": len(empty_bad), "samples": empty_bad[:10]},
                status=FindingStatus.WARN,
                wcag="1.1.1",
            )
        )

    dup_counts = Counter(a.strip() for a in alts)
    duplicates = {text: n for text, n in dup_counts.items() if n > 1}
    if duplicates:
        findings.append(
            _finding(
                id="a11y.images.duplicate_alt",
                rule_id="images.duplicate_alt",
                category=AccessibilityCategory.IMAGES,
                severity=Severity.LOW,
                title="Duplicate alt text",
                description="Multiple images share identical non-empty alt text.",
                location="body > img",
                element="img",
                evidence={"duplicates": dict(list(duplicates.items())[:10])},
                status=FindingStatus.WARN,
                wcag="1.1.1",
            )
        )

    return tuple(findings)


# ---------------------------------------------------------------------------
# Forms — WCAG 1.3.1 / 4.1.2
# ---------------------------------------------------------------------------


def check_forms(document: Document, signals: AccessibilitySignals) -> tuple[Finding, ...]:
    findings: list[Finding] = []

    # Prefer Document.forms for has_label; supplement with signals.inputs.
    unlabelled_doc: list[dict] = []
    for fi, form in enumerate(document.forms):
        for ii, control in enumerate(form.inputs):
            ctype = (control.type or "").lower()
            if ctype in {"hidden", "submit", "button", "reset", "image"}:
                continue
            if not control.has_label:
                unlabelled_doc.append(
                    {
                        "form_index": fi,
                        "input_index": ii,
                        "name": control.name,
                        "id": control.id,
                        "type": control.type,
                    }
                )

    if unlabelled_doc:
        findings.append(
            _finding(
                id="a11y.forms.missing_label",
                rule_id="forms.missing_label",
                category=AccessibilityCategory.FORMS,
                severity=Severity.HIGH,
                title="Missing label",
                description=f"{len(unlabelled_doc)} form control(s) lack an associated label.",
                location="form",
                element="input",
                evidence={"count": len(unlabelled_doc), "samples": unlabelled_doc[:10]},
                wcag="1.3.1",
            )
        )

    missing_name: list[dict] = []
    missing_placeholder: list[dict] = []
    missing_autocomplete: list[dict] = []
    for idx, inp in enumerate(signals.inputs):
        name = _accessible_name(inp.aria_label, inp.aria_labelledby, inp.title, inp.placeholder)
        labelled = inp.has_label or bool(name)
        if not labelled:
            missing_name.append(
                {
                    "index": idx,
                    "tag": inp.tag,
                    "type": inp.type,
                    "name": inp.name,
                    "id": inp.id,
                }
            )
        if not (inp.placeholder or "").strip():
            missing_placeholder.append({"index": idx, "type": inp.type, "name": inp.name})
        itype = (inp.type or "").lower()
        if itype in AUTOCOMPLETE_EXPECTED_TYPES and not (inp.autocomplete or "").strip():
            # name-like fields
            field_name = (inp.name or inp.id or "").lower()
            if any(
                token in field_name
                for token in ("email", "pass", "user", "name", "tel", "phone", "search")
            ) or itype in {"email", "password", "tel"}:
                missing_autocomplete.append(
                    {"index": idx, "type": inp.type, "name": inp.name, "id": inp.id}
                )

    # Avoid double-reporting the same missing-label issue if Document already covered it.
    if missing_name and not unlabelled_doc:
        findings.append(
            _finding(
                id="a11y.forms.missing_accessible_name",
                rule_id="forms.missing_accessible_name",
                category=AccessibilityCategory.FORMS,
                severity=Severity.HIGH,
                title="Missing accessible name",
                description=(
                    f"{len(missing_name)} control(s) lack label, aria-label, or other name."
                ),
                location="form",
                element="input",
                evidence={"count": len(missing_name), "samples": missing_name[:10]},
                wcag="4.1.2",
            )
        )
    elif missing_name and unlabelled_doc:
        # Still emit accessible-name finding only for controls with no aria/title either —
        # already covered by missing_label; skip duplicate HIGH. Emit nothing extra.
        pass

    if missing_placeholder:
        findings.append(
            _finding(
                id="a11y.forms.missing_placeholder",
                rule_id="forms.missing_placeholder",
                category=AccessibilityCategory.FORMS,
                severity=Severity.INFO,
                title="Missing placeholder",
                description=(
                    f"{len(missing_placeholder)} control(s) have no placeholder "
                    "(informational only; placeholders are not a label substitute)."
                ),
                location="form",
                element="input",
                evidence={"count": len(missing_placeholder), "samples": missing_placeholder[:10]},
                status=FindingStatus.INFO,
                wcag="1.3.1",
            )
        )

    if missing_autocomplete:
        findings.append(
            _finding(
                id="a11y.forms.missing_autocomplete",
                rule_id="forms.missing_autocomplete",
                category=AccessibilityCategory.FORMS,
                severity=Severity.LOW,
                title="Missing autocomplete",
                description=(
                    f"{len(missing_autocomplete)} personal-data control(s) lack autocomplete."
                ),
                location="form",
                element="input",
                evidence={"count": len(missing_autocomplete), "samples": missing_autocomplete[:10]},
                status=FindingStatus.WARN,
                wcag="1.3.5",
            )
        )

    return tuple(findings)


# ---------------------------------------------------------------------------
# Buttons — WCAG 4.1.2
# ---------------------------------------------------------------------------


def check_buttons(_document: Document, signals: AccessibilitySignals) -> tuple[Finding, ...]:
    findings: list[Finding] = []
    empty: list[dict] = []
    icon_only: list[dict] = []

    for idx, btn in enumerate(signals.buttons):
        name = _accessible_name(btn.text, btn.aria_label, btn.aria_labelledby, btn.title)
        sample = {
            "index": idx,
            "text": btn.text,
            "type": btn.type,
            "aria_label": btn.aria_label,
        }
        if not name:
            if btn.has_img_child or btn.type == "image":
                icon_only.append(sample)
            else:
                empty.append(sample)

    if empty:
        findings.append(
            _finding(
                id="a11y.buttons.empty",
                rule_id="buttons.empty",
                category=AccessibilityCategory.BUTTONS,
                severity=Severity.HIGH,
                title="Empty button",
                description=f"{len(empty)} button(s) have no accessible name.",
                location="button",
                element="button",
                evidence={"count": len(empty), "samples": empty[:10]},
                wcag="4.1.2",
            )
        )
    if icon_only:
        findings.append(
            _finding(
                id="a11y.buttons.icon_only_unlabelled",
                rule_id="buttons.icon_only_unlabelled",
                category=AccessibilityCategory.BUTTONS,
                severity=Severity.HIGH,
                title="Icon-only button without accessible label",
                description=(
                    f"{len(icon_only)} icon-only button(s) lack aria-label / accessible name."
                ),
                location="button",
                element="button",
                evidence={"count": len(icon_only), "samples": icon_only[:10]},
                wcag="4.1.2",
            )
        )

    return tuple(findings)


# ---------------------------------------------------------------------------
# Links — WCAG 2.4.4 / 4.1.2
# ---------------------------------------------------------------------------


def check_links(document: Document, _signals: AccessibilitySignals) -> tuple[Finding, ...]:
    findings: list[Finding] = []
    empty: list[dict] = []
    generic: list[dict] = []

    for idx, link in enumerate(document.links):
        if link.kind != "anchor":
            continue
        text = (link.text or "").strip()
        name = _accessible_name(text, link.title)
        sample = {"index": idx, "href": link.href, "text": link.text}
        if not name:
            empty.append(sample)
        elif text.lower() in GENERIC_LINK_TEXTS:
            generic.append(sample)

    if empty:
        findings.append(
            _finding(
                id="a11y.links.empty_anchor_text",
                rule_id="links.empty_anchor_text",
                category=AccessibilityCategory.LINKS,
                severity=Severity.HIGH,
                title="Empty anchor text",
                description=f"{len(empty)} link(s) have no accessible name.",
                location="a",
                element="a",
                evidence={"count": len(empty), "samples": empty[:10]},
                wcag="2.4.4",
            )
        )
        findings.append(
            _finding(
                id="a11y.links.missing_accessible_name",
                rule_id="links.missing_accessible_name",
                category=AccessibilityCategory.LINKS,
                severity=Severity.HIGH,
                title="Missing accessible name",
                description=f"{len(empty)} link(s) lack text and title for an accessible name.",
                location="a",
                element="a",
                evidence={"count": len(empty), "samples": empty[:10]},
                wcag="4.1.2",
            )
        )

    if generic:
        findings.append(
            _finding(
                id="a11y.links.generic_anchor_text",
                rule_id="links.generic_anchor_text",
                category=AccessibilityCategory.LINKS,
                severity=Severity.MEDIUM,
                title="Generic anchor text",
                description=f"{len(generic)} link(s) use non-descriptive text such as 'click here'.",
                location="a",
                element="a",
                evidence={"count": len(generic), "samples": generic[:10]},
                status=FindingStatus.WARN,
                wcag="2.4.4",
            )
        )

    return tuple(findings)


# ---------------------------------------------------------------------------
# Headings — WCAG 1.3.1
# ---------------------------------------------------------------------------


def check_headings(document: Document, _signals: AccessibilitySignals) -> tuple[Finding, ...]:
    findings: list[Finding] = []
    headings = document.headings
    h1s = [h for h in headings if h.level == 1]

    if not h1s:
        findings.append(
            _finding(
                id="a11y.headings.missing_h1",
                rule_id="headings.missing_h1",
                category=AccessibilityCategory.HEADINGS,
                severity=Severity.HIGH,
                title="Missing H1",
                description="The document has no H1 heading.",
                location="body",
                element="h1",
                evidence={"h1_count": 0},
                wcag="1.3.1",
            )
        )
    elif len(h1s) > 1:
        findings.append(
            _finding(
                id="a11y.headings.multiple_h1",
                rule_id="headings.multiple_h1",
                category=AccessibilityCategory.HEADINGS,
                severity=Severity.MEDIUM,
                title="Multiple H1",
                description=f"Found {len(h1s)} H1 headings; a single H1 is preferred.",
                location="body",
                element="h1",
                evidence={"h1_count": len(h1s), "texts": [h.text for h in h1s]},
                status=FindingStatus.WARN,
                wcag="1.3.1",
            )
        )

    if headings:
        levels = [h.level for h in headings]
        prev = levels[0]
        for level in levels[1:]:
            if level > prev + 1:
                findings.append(
                    _finding(
                        id="a11y.headings.skipped_levels",
                        rule_id="headings.skipped_levels",
                        category=AccessibilityCategory.HEADINGS,
                        severity=Severity.MEDIUM,
                        title="Skipped heading levels",
                        description=f"Heading levels jump from h{prev} to h{level}.",
                        location="body",
                        element=f"h{level}",
                        evidence={"from_level": prev, "to_level": level, "levels": levels},
                        status=FindingStatus.WARN,
                        wcag="1.3.1",
                    )
                )
                break
            prev = level

    empty = [h for h in headings if not (h.text or "").strip()]
    if empty:
        findings.append(
            _finding(
                id="a11y.headings.empty",
                rule_id="headings.empty",
                category=AccessibilityCategory.HEADINGS,
                severity=Severity.MEDIUM,
                title="Empty headings",
                description=f"Found {len(empty)} heading(s) with empty text.",
                location="body",
                element="heading",
                evidence={"count": len(empty), "orders": [h.order for h in empty]},
                status=FindingStatus.WARN,
                wcag="1.3.1",
            )
        )

    return tuple(findings)


# ---------------------------------------------------------------------------
# Language — WCAG 3.1.1
# ---------------------------------------------------------------------------


def check_language(document: Document, _signals: AccessibilitySignals) -> tuple[Finding, ...]:
    findings: list[Finding] = []
    lang = document.language

    if not lang or not str(lang).strip():
        findings.append(
            _finding(
                id="a11y.language.missing",
                rule_id="language.missing",
                category=AccessibilityCategory.LANGUAGE,
                severity=Severity.MEDIUM,
                title="Missing html lang",
                description="The root <html> element has no lang attribute.",
                location="html",
                element="html",
                evidence={"observed": None},
                wcag="3.1.1",
            )
        )
        return tuple(findings)

    value = str(lang).strip()
    if not _LANG_RE.match(value):
        findings.append(
            _finding(
                id="a11y.language.invalid",
                rule_id="language.invalid",
                category=AccessibilityCategory.LANGUAGE,
                severity=Severity.LOW,
                title="Invalid language code",
                description=f"Language code '{value}' failed basic BCP 47 validation.",
                location="html",
                element="html",
                evidence={"observed": value},
                status=FindingStatus.WARN,
                wcag="3.1.1",
            )
        )

    return tuple(findings)


# ---------------------------------------------------------------------------
# ARIA — WCAG 4.1.2
# ---------------------------------------------------------------------------


def check_aria(_document: Document, signals: AccessibilitySignals) -> tuple[Finding, ...]:
    findings: list[Finding] = []

    if signals.duplicate_ids:
        findings.append(
            _finding(
                id="a11y.aria.duplicate_ids",
                rule_id="aria.duplicate_ids",
                category=AccessibilityCategory.ARIA,
                severity=Severity.HIGH,
                title="Duplicate IDs",
                description=f"Found {len(signals.duplicate_ids)} duplicate id value(s).",
                location="document",
                element="*",
                evidence={"ids": list(signals.duplicate_ids)[:20]},
                wcag="4.1.1",
            )
        )

    if signals.invalid_aria_attributes:
        findings.append(
            _finding(
                id="a11y.aria.invalid_attributes",
                rule_id="aria.invalid_attributes",
                category=AccessibilityCategory.ARIA,
                severity=Severity.MEDIUM,
                title="Invalid aria-* attributes",
                description=(
                    f"{len(signals.invalid_aria_attributes)} unrecognized aria-* "
                    "attribute name(s)."
                ),
                location="document",
                element="*",
                evidence={"attributes": list(signals.invalid_aria_attributes)[:20]},
                status=FindingStatus.WARN,
                wcag="4.1.2",
            )
        )

    if signals.invalid_roles:
        findings.append(
            _finding(
                id="a11y.aria.invalid_role",
                rule_id="aria.invalid_role",
                category=AccessibilityCategory.ARIA,
                severity=Severity.HIGH,
                title="Invalid ARIA role",
                description=f"Unrecognized ARIA role(s): {', '.join(signals.invalid_roles[:10])}.",
                location="document",
                element="*",
                evidence={"roles": list(signals.invalid_roles)[:20]},
                wcag="4.1.2",
            )
        )

    # Icon buttons / inputs that expect aria-label are covered in buttons/forms;
    # emit a focused finding when buttons already flagged icon-only.
    expect_label = [
        {"index": i, "type": b.type}
        for i, b in enumerate(signals.buttons)
        if (b.has_img_child or b.type == "image")
        and not _accessible_name(b.text, b.aria_label, b.aria_labelledby, b.title)
    ]
    if expect_label:
        findings.append(
            _finding(
                id="a11y.aria.missing_aria_label",
                rule_id="aria.missing_aria_label",
                category=AccessibilityCategory.ARIA,
                severity=Severity.HIGH,
                title="Missing aria-label where expected",
                description=(
                    f"{len(expect_label)} control(s) appear to need an aria-label "
                    "for an accessible name."
                ),
                location="button",
                element="button",
                evidence={"count": len(expect_label), "samples": expect_label[:10]},
                wcag="4.1.2",
            )
        )

    return tuple(findings)


# ---------------------------------------------------------------------------
# Landmarks — WCAG 1.3.1 / 2.4.1
# ---------------------------------------------------------------------------


def check_landmarks(_document: Document, signals: AccessibilitySignals) -> tuple[Finding, ...]:
    findings: list[Finding] = []
    if not signals.has_main:
        findings.append(
            _finding(
                id="a11y.landmarks.missing_main",
                rule_id="landmarks.missing_main",
                category=AccessibilityCategory.LANDMARKS,
                severity=Severity.MEDIUM,
                title="Missing main",
                description="No <main> landmark (or role=main) was found.",
                location="body",
                element="main",
                evidence={"has_main": False},
                status=FindingStatus.WARN,
                wcag="1.3.1",
            )
        )
    if not signals.has_nav:
        findings.append(
            _finding(
                id="a11y.landmarks.missing_navigation",
                rule_id="landmarks.missing_navigation",
                category=AccessibilityCategory.LANDMARKS,
                severity=Severity.LOW,
                title="Missing navigation",
                description="No <nav> landmark (or role=navigation) was found.",
                location="body",
                element="nav",
                evidence={"has_nav": False},
                status=FindingStatus.WARN,
                wcag="1.3.1",
            )
        )
    if not signals.has_header:
        findings.append(
            _finding(
                id="a11y.landmarks.missing_header",
                rule_id="landmarks.missing_header",
                category=AccessibilityCategory.LANDMARKS,
                severity=Severity.INFO,
                title="Missing header",
                description="No <header> landmark (or role=banner) was found.",
                location="body",
                element="header",
                evidence={"has_header": False},
                status=FindingStatus.INFO,
                wcag="1.3.1",
            )
        )
    if not signals.has_footer:
        findings.append(
            _finding(
                id="a11y.landmarks.missing_footer",
                rule_id="landmarks.missing_footer",
                category=AccessibilityCategory.LANDMARKS,
                severity=Severity.INFO,
                title="Missing footer",
                description="No <footer> landmark (or role=contentinfo) was found.",
                location="body",
                element="footer",
                evidence={"has_footer": False},
                status=FindingStatus.INFO,
                wcag="1.3.1",
            )
        )
    return tuple(findings)


# ---------------------------------------------------------------------------
# Tables — WCAG 1.3.1
# ---------------------------------------------------------------------------


def check_tables(_document: Document, signals: AccessibilitySignals) -> tuple[Finding, ...]:
    findings: list[Finding] = []
    no_headers: list[dict] = []
    no_caption: list[dict] = []
    for idx, table in enumerate(signals.tables):
        if not table.has_th and not table.has_headers_attr:
            no_headers.append({"index": idx})
        if not table.has_caption:
            no_caption.append({"index": idx})

    if no_headers:
        findings.append(
            _finding(
                id="a11y.tables.missing_headers",
                rule_id="tables.missing_headers",
                category=AccessibilityCategory.TABLES,
                severity=Severity.HIGH,
                title="Missing table headers",
                description=f"{len(no_headers)} table(s) lack <th> or headers attributes.",
                location="table",
                element="table",
                evidence={"count": len(no_headers), "samples": no_headers[:10]},
                wcag="1.3.1",
            )
        )
    if no_caption:
        findings.append(
            _finding(
                id="a11y.tables.missing_caption",
                rule_id="tables.missing_caption",
                category=AccessibilityCategory.TABLES,
                severity=Severity.LOW,
                title="Missing caption",
                description=f"{len(no_caption)} table(s) lack a <caption>.",
                location="table",
                element="caption",
                evidence={"count": len(no_caption), "samples": no_caption[:10]},
                status=FindingStatus.WARN,
                wcag="1.3.1",
            )
        )
    return tuple(findings)


# ---------------------------------------------------------------------------
# Media — WCAG 1.2.2 / 1.2.1
# ---------------------------------------------------------------------------


def check_media(_document: Document, signals: AccessibilitySignals) -> tuple[Finding, ...]:
    findings: list[Finding] = []
    no_captions = [
        {"index": i} for i, v in enumerate(signals.videos) if not v.has_track_captions
    ]
    if no_captions:
        findings.append(
            _finding(
                id="a11y.media.video_missing_captions",
                rule_id="media.video_missing_captions",
                category=AccessibilityCategory.MEDIA,
                severity=Severity.HIGH,
                title="Video without captions",
                description=(
                    f"{len(no_captions)} <video> element(s) lack a captions/subtitles track."
                ),
                location="video",
                element="video",
                evidence={"count": len(no_captions), "samples": no_captions[:10]},
                wcag="1.2.2",
            )
        )

    no_transcript = [
        {"index": i, "aria_label": a.aria_label}
        for i, a in enumerate(signals.audio)
        if not a.has_transcript_hint
    ]
    if no_transcript:
        findings.append(
            _finding(
                id="a11y.media.audio_missing_transcript",
                rule_id="media.audio_missing_transcript",
                category=AccessibilityCategory.MEDIA,
                severity=Severity.MEDIUM,
                title="Audio without transcript hint",
                description=(
                    f"{len(no_transcript)} <audio> element(s) show no transcript hint."
                ),
                location="audio",
                element="audio",
                evidence={"count": len(no_transcript), "samples": no_transcript[:10]},
                status=FindingStatus.WARN,
                wcag="1.2.1",
            )
        )
    return tuple(findings)


# ---------------------------------------------------------------------------
# Navigation / Focus / Semantics / Documents
# ---------------------------------------------------------------------------


def check_navigation(_document: Document, signals: AccessibilitySignals) -> tuple[Finding, ...]:
    if signals.has_skip_link:
        return ()
    return (
        _finding(
            id="a11y.navigation.missing_skip_link",
            rule_id="navigation.missing_skip_link",
            category=AccessibilityCategory.NAVIGATION,
            severity=Severity.MEDIUM,
            title="Missing skip link",
            description="No early skip-to-content link was detected.",
            location="body",
            element="a",
            evidence={"has_skip_link": False},
            status=FindingStatus.WARN,
            wcag="2.4.1",
        ),
    )


def check_focus(_document: Document, signals: AccessibilitySignals) -> tuple[Finding, ...]:
    """Positive tabindex and onclick on non-focusable elements (WCAG 2.1.1 / 2.4.3)."""
    findings: list[Finding] = []
    bad_tabindex = [
        c.model_dump()
        for c in signals.clickable_non_semantic
        if c.tabindex and c.tabindex.lstrip("-").isdigit() and int(c.tabindex) > 0
    ]
    if bad_tabindex:
        findings.append(
            _finding(
                id="a11y.focus.positive_tabindex",
                rule_id="focus.positive_tabindex",
                category=AccessibilityCategory.FOCUS,
                severity=Severity.MEDIUM,
                title="Positive tabindex",
                description="Elements use tabindex greater than 0, which disrupts focus order.",
                location="document",
                element="*",
                evidence={"count": len(bad_tabindex), "samples": bad_tabindex[:10]},
                status=FindingStatus.WARN,
                wcag="2.4.3",
            )
        )
    return tuple(findings)


def check_semantics(_document: Document, signals: AccessibilitySignals) -> tuple[Finding, ...]:
    findings: list[Finding] = []
    clickable = [
        c.model_dump()
        for c in signals.clickable_non_semantic
        if c.has_onclick and c.tag in {"div", "span"}
    ]
    if clickable:
        findings.append(
            _finding(
                id="a11y.semantics.clickable_divs",
                rule_id="semantics.clickable_divs",
                category=AccessibilityCategory.SEMANTICS,
                severity=Severity.MEDIUM,
                title="Clickable divs",
                description=(
                    f"{len(clickable)} non-semantic element(s) use onclick without a "
                    "native interactive element."
                ),
                location="body",
                element="div",
                evidence={"count": len(clickable), "samples": clickable[:10]},
                status=FindingStatus.WARN,
                wcag="2.1.1",
            )
        )

    # Heuristic: many divs, almost no semantic structure.
    if signals.div_count >= 15 and signals.semantic_count < 3 and not signals.has_main:
        findings.append(
            _finding(
                id="a11y.semantics.missing_semantic_elements",
                rule_id="semantics.missing_semantic_elements",
                category=AccessibilityCategory.SEMANTICS,
                severity=Severity.LOW,
                title="Missing semantic elements",
                description=(
                    "Page markup appears div-heavy with few detectable semantic elements."
                ),
                location="body",
                element="*",
                evidence={
                    "div_count": signals.div_count,
                    "semantic_count": signals.semantic_count,
                },
                status=FindingStatus.INFO,
                wcag="1.3.1",
            )
        )
    return tuple(findings)


def check_document(document: Document, _signals: AccessibilitySignals) -> tuple[Finding, ...]:
    findings: list[Finding] = []
    if document.title is None or not str(document.title).strip():
        findings.append(
            _finding(
                id="a11y.documents.missing_title",
                rule_id="documents.missing_title",
                category=AccessibilityCategory.DOCUMENTS,
                severity=Severity.HIGH,
                title="Missing title",
                description="The document has no usable <title>.",
                location="head > title",
                element="title",
                evidence={"observed": document.title},
                wcag="2.4.2",
            )
        )
    if not document.charset or not str(document.charset).strip():
        findings.append(
            _finding(
                id="a11y.documents.missing_charset",
                rule_id="documents.missing_charset",
                category=AccessibilityCategory.DOCUMENTS,
                severity=Severity.MEDIUM,
                title="Missing meta charset",
                description="No document character encoding was detected.",
                location="head",
                element="meta",
                evidence={"observed": document.charset},
                status=FindingStatus.WARN,
                wcag="4.1.1",
            )
        )
    if not document.viewport or not str(document.viewport).strip():
        findings.append(
            _finding(
                id="a11y.documents.missing_viewport",
                rule_id="documents.missing_viewport",
                category=AccessibilityCategory.DOCUMENTS,
                severity=Severity.MEDIUM,
                title="Missing viewport",
                description="No <meta name='viewport'> was found.",
                location="head > meta[name=viewport]",
                element="meta",
                evidence={"observed": None},
                status=FindingStatus.WARN,
                wcag="1.4.10",
            )
        )
    return tuple(findings)


ALL_RULES: Sequence[RuleFn] = (
    check_images,
    check_forms,
    check_buttons,
    check_links,
    check_headings,
    check_language,
    check_aria,
    check_landmarks,
    check_tables,
    check_media,
    check_navigation,
    check_focus,
    check_semantics,
    check_document,
)

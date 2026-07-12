"""
Accessibility Intelligence Engine — rules & findings reference (Sprint 9).

## Purpose

Produce **Accessibility Findings** from an immutable ``Document``. This engine does **not**:

- calculate accessibility scores
- generate recommendations
- run browsers / Lighthouse / axe
- re-parse with BeautifulSoup
- persist results or change APIs

## Input

``AuditContext.shared_state["document"]``

Supplemental signals are derived once from ``Document.html`` via stdlib
``html.parser.HTMLParser`` (landmarks, buttons, tables, media, ARIA, IDs).

## Output

``AccessibilityAnalysis`` at ``context.shared_state["accessibility_analysis"]``:

| Field | Description |
|---|---|
| findings | Ordered ``Finding`` tuple (shared model) |
| warnings | Parser warnings forwarded |
| summary | Counts by severity/category + message |
| statistics | Aggregate counts |

## Severity

| Value | Meaning |
|---|---|
| info | Informational |
| low | Minor |
| medium | Notable |
| high | Important barrier |
| critical | Severe (reserved; unused in Sprint 9 static set) |

## Categories

Images, Forms, Buttons, Links, Headings, ARIA, Landmarks, Language, Tables,
Media, Navigation, Focus, Semantics, Documents.

## Finding fields

``id``, ``rule_id``, ``category``, ``severity``, ``title``, ``description``,
``location``, ``element``, ``evidence`` (includes ``wcag`` when known), ``status``.

## Rules (finding IDs) + WCAG

### Images (1.1.1)
| ID | Severity | When |
|---|---|---|
| a11y.images.missing_alt | high | alt missing |
| a11y.images.empty_alt_inappropriate | medium | empty alt on likely informative image |
| a11y.images.duplicate_alt | low | identical non-empty alt on 2+ images |

### Forms (1.3.1 / 4.1.2 / 1.3.5)
| ID | Severity | When |
|---|---|---|
| a11y.forms.missing_label | high | control without associated label |
| a11y.forms.missing_accessible_name | high | no label/aria-label/title (signals path) |
| a11y.forms.missing_placeholder | info | no placeholder (not a failure) |
| a11y.forms.missing_autocomplete | low | personal data fields without autocomplete |

### Buttons (4.1.2)
| ID | Severity | When |
|---|---|---|
| a11y.buttons.empty | high | no accessible name |
| a11y.buttons.icon_only_unlabelled | high | icon/image button without name |

### Links (2.4.4 / 4.1.2)
| ID | Severity | When |
|---|---|---|
| a11y.links.empty_anchor_text | high | empty text |
| a11y.links.missing_accessible_name | high | empty text and title |
| a11y.links.generic_anchor_text | medium | “click here”, “read more”, etc. |

### Headings (1.3.1)
| ID | Severity | When |
|---|---|---|
| a11y.headings.missing_h1 | high | zero H1 |
| a11y.headings.multiple_h1 | medium | >1 H1 |
| a11y.headings.skipped_levels | medium | level jump > 1 |
| a11y.headings.empty | medium | empty heading text |

### Language (3.1.1)
| ID | Severity | When |
|---|---|---|
| a11y.language.missing | medium | no html lang |
| a11y.language.invalid | low | fails basic BCP 47 pattern |

### ARIA (4.1.1 / 4.1.2)
| ID | Severity | When |
|---|---|---|
| a11y.aria.duplicate_ids | high | duplicate id values |
| a11y.aria.invalid_attributes | medium | unknown aria-* names |
| a11y.aria.invalid_role | high | unknown role |
| a11y.aria.missing_aria_label | high | icon controls needing aria-label |

### Landmarks (1.3.1)
| ID | Severity | When |
|---|---|---|
| a11y.landmarks.missing_main | medium | no main |
| a11y.landmarks.missing_navigation | low | no nav |
| a11y.landmarks.missing_header | info | no header/banner |
| a11y.landmarks.missing_footer | info | no footer/contentinfo |

### Tables (1.3.1)
| ID | Severity | When |
|---|---|---|
| a11y.tables.missing_headers | high | no th / headers |
| a11y.tables.missing_caption | low | no caption |

### Media (1.2.2 / 1.2.1)
| ID | Severity | When |
|---|---|---|
| a11y.media.video_missing_captions | high | video without track captions/subtitles |
| a11y.media.audio_missing_transcript | medium | audio without transcript hint |

### Navigation / Focus / Semantics / Documents
| ID | Severity | WCAG | When |
|---|---|---|---|
| a11y.navigation.missing_skip_link | medium | 2.4.1 | no early skip link |
| a11y.focus.positive_tabindex | medium | 2.4.3 | tabindex > 0 |
| a11y.semantics.clickable_divs | medium | 2.1.1 | div/span onclick |
| a11y.semantics.missing_semantic_elements | low | 1.3.1 | div-heavy markup |
| a11y.documents.missing_title | high | 2.4.2 | no title |
| a11y.documents.missing_charset | medium | 4.1.1 | no charset |
| a11y.documents.missing_viewport | medium | 1.4.10 | no viewport |

## Statistics

``images``, ``images_missing_alt``, ``forms``, ``unlabelled_forms``, ``buttons``,
``empty_buttons``, ``links``, ``empty_links``, ``headings``, ``tables``, ``videos``,
``audio``, ``landmarks``, ``aria_attributes``.

## Pipeline

1. URL Validation → 2. Crawler → 3. Parser → 4. SEO → 5. Accessibility (``accessibility``)
"""

"""Template registry — deterministic finding_id → recommendation templates."""

from __future__ import annotations

from dataclasses import dataclass

from app.engines.recommendation.schemas import (
    EffortLevel,
    ImpactLevel,
    RecommendationCategory,
)


@dataclass(frozen=True, slots=True)
class RecommendationTemplate:
    """
    Fixed copy for one recommendation_id.

    Titles/descriptions are static strings — never free-text generation.
    """

    recommendation_id: str
    title: str
    description: str
    technical_reason: str
    business_reason: str
    category: RecommendationCategory
    estimated_effort: EffortLevel
    estimated_impact: ImpactLevel
    related_rules: tuple[str, ...] = ()
    # Finding IDs that produce this recommendation (exact match).
    source_finding_ids: tuple[str, ...] = ()
    # Optional base confidence before occurrence/health adjustments.
    base_confidence: int = 90


def _t(
    recommendation_id: str,
    *,
    title: str,
    description: str,
    technical_reason: str,
    business_reason: str,
    category: RecommendationCategory,
    effort: EffortLevel,
    impact: ImpactLevel,
    findings: tuple[str, ...],
    rules: tuple[str, ...] = (),
    confidence: int = 90,
) -> RecommendationTemplate:
    return RecommendationTemplate(
        recommendation_id=recommendation_id,
        title=title,
        description=description,
        technical_reason=technical_reason,
        business_reason=business_reason,
        category=category,
        estimated_effort=effort,
        estimated_impact=impact,
        related_rules=rules or findings,
        source_finding_ids=findings,
        base_confidence=confidence,
    )


# Explicit templates (Sprint 15 coverage of high-value finding IDs).
TEMPLATES: tuple[RecommendationTemplate, ...] = (
    # --- SEO ---
    _t(
        "rec.seo.add_document_title",
        title="Add a descriptive document title",
        description="Set a unique, descriptive <title> for the page (about 50–60 characters).",
        technical_reason="Title element is missing or empty, weakening crawl and SERP identity.",
        business_reason="Clear titles improve search snippet recognition and click-through potential.",
        category=RecommendationCategory.SEO,
        effort=EffortLevel.VERY_LOW,
        impact=ImpactLevel.HIGH,
        findings=("seo.title.missing", "seo.title.empty", "biz.seo.missing_title_visibility", "biz.seo.empty_title_visibility"),
        rules=("seo.title",),
    ),
    _t(
        "rec.seo.add_meta_description",
        title="Add a compelling meta description",
        description="Provide a unique meta description summarizing the page offer.",
        technical_reason="meta name=description is missing, so SERP snippets may be auto-generated poorly.",
        business_reason="Strong snippets increase organic click-through potential.",
        category=RecommendationCategory.SEO,
        effort=EffortLevel.LOW,
        impact=ImpactLevel.HIGH,
        findings=("seo.meta_description.missing", "biz.marketing.missing_meta_ctr"),
        rules=("seo.meta_description",),
    ),
    _t(
        "rec.seo.fix_h1_hierarchy",
        title="Establish a single clear H1",
        description="Use exactly one H1 that states the primary page topic.",
        technical_reason="Heading structure is missing an H1 or uses multiple H1s.",
        business_reason="Clear hierarchy improves content comprehension and topical signals.",
        category=RecommendationCategory.SEO,
        effort=EffortLevel.LOW,
        impact=ImpactLevel.HIGH,
        findings=(
            "seo.headings.missing_h1",
            "seo.headings.multiple_h1",
            "biz.seo.missing_h1_hierarchy",
            "biz.seo.multiple_h1_hierarchy",
            "biz.ux.multiple_h1",
        ),
        rules=("seo.headings",),
    ),
    _t(
        "rec.seo.fix_heading_order",
        title="Fix skipped heading levels",
        description="Order headings sequentially (H1→H2→H3) without skipping levels.",
        technical_reason="Heading levels skip in the document outline.",
        business_reason="Broken outlines increase cognitive load and hurt accessibility.",
        category=RecommendationCategory.SEO,
        effort=EffortLevel.MEDIUM,
        impact=ImpactLevel.MEDIUM,
        findings=("seo.headings.skipped_hierarchy", "a11y.headings.skipped_levels", "biz.ux.broken_heading_hierarchy", "biz.ux.skipped_headings"),
        rules=("seo.headings", "a11y.headings"),
    ),
    _t(
        "rec.seo.add_canonical",
        title="Add a canonical URL",
        description="Declare a canonical link element pointing to the preferred URL.",
        technical_reason="Canonical signal is missing, risking duplicate-content ambiguity.",
        business_reason="Canonicalization concentrates ranking signals on the preferred URL.",
        category=RecommendationCategory.SEO,
        effort=EffortLevel.LOW,
        impact=ImpactLevel.MEDIUM,
        findings=("seo.canonical.missing",),
        rules=("seo.canonical",),
    ),
    _t(
        "rec.seo.add_viewport",
        title="Add a mobile viewport meta tag",
        description="Include <meta name=\"viewport\" content=\"width=device-width, initial-scale=1\">.",
        technical_reason="Viewport meta is missing; mobile rendering is unreliable.",
        business_reason="Poor mobile layout increases bounce and reduces conversion.",
        category=RecommendationCategory.SEO,
        effort=EffortLevel.VERY_LOW,
        impact=ImpactLevel.HIGH,
        findings=("seo.viewport.missing", "a11y.documents.missing_viewport", "biz.conversion.missing_viewport_mobile", "biz.conversion.a11y_missing_viewport"),
        rules=("seo.viewport",),
    ),
    _t(
        "rec.seo.add_lang",
        title="Declare the document language",
        description="Set the html lang attribute to the primary language code.",
        technical_reason="html[lang] is missing.",
        business_reason="Language declaration aids accessibility and localized search presentation.",
        category=RecommendationCategory.SEO,
        effort=EffortLevel.VERY_LOW,
        impact=ImpactLevel.MEDIUM,
        findings=("seo.language.missing", "a11y.language.missing", "biz.marketing.missing_lang"),
        rules=("seo.language",),
    ),
    # --- Accessibility ---
    _t(
        "rec.a11y.add_image_alt",
        title="Add meaningful image alt text",
        description="Provide descriptive alt attributes for informative images; use empty alt for decorative ones.",
        technical_reason="One or more images lack alt text.",
        business_reason="Alt text expands inclusive reach and can support image discovery.",
        category=RecommendationCategory.ACCESSIBILITY,
        effort=EffortLevel.LOW,
        impact=ImpactLevel.HIGH,
        findings=("seo.images.missing_alt", "a11y.images.missing_alt", "biz.a11y.missing_alt_reach", "biz.a11y.alt_compliance"),
        rules=("a11y.images", "seo.images"),
    ),
    _t(
        "rec.a11y.label_form_controls",
        title="Label all form controls",
        description="Associate every input with a visible <label> or accessible name.",
        technical_reason="Form controls are missing labels or accessible names.",
        business_reason="Unlabeled fields create conversion friction and exclude assistive-tech users.",
        category=RecommendationCategory.ACCESSIBILITY,
        effort=EffortLevel.LOW,
        impact=ImpactLevel.HIGH,
        findings=(
            "a11y.forms.missing_label",
            "a11y.forms.missing_accessible_name",
            "biz.conversion.missing_labels_friction",
            "biz.conversion.missing_accessible_name",
        ),
        rules=("a11y.forms",),
    ),
    _t(
        "rec.a11y.name_buttons",
        title="Give buttons accessible names",
        description="Ensure every button has visible text or an accessible name.",
        technical_reason="Empty or unnamed buttons were detected.",
        business_reason="Unnamed CTAs reduce conversion clarity and fail accessibility checks.",
        category=RecommendationCategory.ACCESSIBILITY,
        effort=EffortLevel.VERY_LOW,
        impact=ImpactLevel.HIGH,
        findings=("a11y.buttons.empty", "biz.conversion.empty_buttons"),
        rules=("a11y.buttons",),
    ),
    _t(
        "rec.a11y.add_main_landmark",
        title="Add a main landmark",
        description="Wrap primary content in a <main> landmark (or role=main).",
        technical_reason="No main landmark was found.",
        business_reason="Landmarks help users and AT skip to primary content faster.",
        category=RecommendationCategory.ACCESSIBILITY,
        effort=EffortLevel.LOW,
        impact=ImpactLevel.MEDIUM,
        findings=("a11y.landmarks.missing_main", "biz.a11y.missing_main_landmark"),
        rules=("a11y.landmarks",),
    ),
    # --- Security ---
    _t(
        "rec.sec.enforce_https",
        title="Serve the site exclusively over HTTPS",
        description="Redirect HTTP to HTTPS and ensure all assets load securely.",
        technical_reason="Page URL or assets indicate non-HTTPS usage.",
        business_reason="HTTPS is baseline trust for visitors and payment/lead forms.",
        category=RecommendationCategory.SECURITY,
        effort=EffortLevel.MEDIUM,
        impact=ImpactLevel.CRITICAL,
        findings=("sec.https.non_https_url", "biz.trust.http_page", "sec.mixed.http_script", "sec.forms.sensitive_over_http", "biz.revenue.sensitive_http_forms"),
        rules=("sec.https",),
    ),
    _t(
        "rec.sec.add_csp",
        title="Deploy a Content-Security-Policy",
        description="Add a CSP header that restricts script and resource origins.",
        technical_reason="Content-Security-Policy response header is missing.",
        business_reason="CSP reduces XSS blast radius and strengthens brand trust.",
        category=RecommendationCategory.SECURITY,
        effort=EffortLevel.HIGH,
        impact=ImpactLevel.HIGH,
        findings=("sec.headers.missing_csp", "biz.trust.missing_csp"),
        rules=("sec.headers.csp",),
    ),
    _t(
        "rec.sec.add_hsts",
        title="Enable HTTP Strict Transport Security",
        description="Send Strict-Transport-Security with an appropriate max-age after HTTPS is stable.",
        technical_reason="HSTS header is missing.",
        business_reason="HSTS prevents protocol downgrade and cookie hijack on repeat visits.",
        category=RecommendationCategory.SECURITY,
        effort=EffortLevel.LOW,
        impact=ImpactLevel.HIGH,
        findings=("sec.headers.missing_hsts", "biz.trust.missing_hsts"),
        rules=("sec.headers.hsts",),
    ),
    _t(
        "rec.sec.add_xfo",
        title="Set X-Frame-Options or frame-ancestors",
        description="Prevent clickjacking with X-Frame-Options or CSP frame-ancestors.",
        technical_reason="Clickjacking protection header is missing.",
        business_reason="Framing attacks can trick users into unintended actions.",
        category=RecommendationCategory.SECURITY,
        effort=EffortLevel.VERY_LOW,
        impact=ImpactLevel.MEDIUM,
        findings=("sec.headers.missing_xfo",),
        rules=("sec.headers.xfo",),
    ),
    _t(
        "rec.sec.harden_cookies",
        title="Mark cookies Secure (and Prefer HttpOnly)",
        description="Set Secure on cookies sent over HTTPS; prefer HttpOnly for session cookies.",
        technical_reason="Cookies lack Secure attributes.",
        business_reason="Insecure cookies increase session theft risk.",
        category=RecommendationCategory.SECURITY,
        effort=EffortLevel.LOW,
        impact=ImpactLevel.HIGH,
        findings=("sec.cookies.missing_secure",),
        rules=("sec.cookies",),
    ),
    _t(
        "rec.sec.reduce_server_disclosure",
        title="Reduce server identity disclosure",
        description="Omit or minimize Server / X-Powered-By response headers.",
        technical_reason="Server technology headers disclose stack details.",
        business_reason="Unnecessary disclosure aids attackers during reconnaissance.",
        category=RecommendationCategory.SECURITY,
        effort=EffortLevel.VERY_LOW,
        impact=ImpactLevel.LOW,
        findings=("sec.disclosure.server_header", "biz.brand.server_disclosure"),
        rules=("sec.disclosure",),
    ),
    # --- Performance ---
    _t(
        "rec.perf.enable_lazy_images",
        title="Enable lazy-loading for below-the-fold images",
        description="Add loading=\"lazy\" (or equivalent) to offscreen images.",
        technical_reason="Images lack lazy-loading hints.",
        business_reason="Faster initial load improves engagement on media-heavy pages.",
        category=RecommendationCategory.PERFORMANCE,
        effort=EffortLevel.LOW,
        impact=ImpactLevel.HIGH,
        findings=("perf.images.missing_lazy_loading", "biz.perf.missing_lazy_experience"),
        rules=("perf.images",),
    ),
    _t(
        "rec.perf.reduce_dom_size",
        title="Reduce DOM size and depth",
        description="Simplify markup, paginate heavy lists, and avoid deeply nested wrappers.",
        technical_reason="DOM node count or depth exceeds recommended thresholds.",
        business_reason="Large DOMs slow interaction and raise bounce risk on low-end devices.",
        category=RecommendationCategory.PERFORMANCE,
        effort=EffortLevel.HIGH,
        impact=ImpactLevel.HIGH,
        findings=("perf.dom.excessive_nodes", "perf.dom.excessive_depth", "biz.perf.large_dom_cost"),
        rules=("perf.dom",),
    ),
    _t(
        "rec.perf.defer_scripts",
        title="Defer non-critical JavaScript",
        description="Add defer/async to non-critical scripts and reduce total script count.",
        technical_reason="Many scripts lack defer/async or script count is high.",
        business_reason="Faster interactivity supports conversion on content and commerce pages.",
        category=RecommendationCategory.PERFORMANCE,
        effort=EffortLevel.MEDIUM,
        impact=ImpactLevel.HIGH,
        findings=("perf.js.missing_defer", "perf.js.missing_async", "perf.js.large_script_count", "biz.perf.large_scripts"),
        rules=("perf.js",),
    ),
    _t(
        "rec.perf.add_cache_headers",
        title="Add cache-control for static assets",
        description="Send Cache-Control (and validators) for cacheable static resources.",
        technical_reason="Cache-Control is missing on responses.",
        business_reason="Caching cuts repeat-view latency and origin cost.",
        category=RecommendationCategory.PERFORMANCE,
        effort=EffortLevel.MEDIUM,
        impact=ImpactLevel.MEDIUM,
        findings=("perf.caching.missing_cache_control", "biz.perf.missing_cache_control"),
        rules=("perf.caching",),
    ),
    _t(
        "rec.perf.enable_compression",
        title="Enable response compression",
        description="Serve gzip or brotli Content-Encoding for text assets.",
        technical_reason="Content-Encoding compression was not observed.",
        business_reason="Smaller payloads improve load time on constrained networks.",
        category=RecommendationCategory.INFRASTRUCTURE,
        effort=EffortLevel.LOW,
        impact=ImpactLevel.MEDIUM,
        findings=("perf.compression.missing_content_encoding", "biz.perf.missing_compression"),
        rules=("perf.compression",),
    ),
    _t(
        "rec.perf.reduce_render_blocking_css",
        title="Reduce render-blocking CSS",
        description="Inline critical CSS and defer non-critical stylesheets.",
        technical_reason="Render-blocking stylesheets delay first paint.",
        business_reason="Faster first paint improves perceived performance.",
        category=RecommendationCategory.PERFORMANCE,
        effort=EffortLevel.HIGH,
        impact=ImpactLevel.HIGH,
        findings=("perf.css.render_blocking", "biz.perf.render_blocking_css"),
        rules=("perf.css",),
    ),
    _t(
        "rec.perf.limit_third_parties",
        title="Audit and limit third-party domains",
        description="Remove unused vendors and load remaining third parties asynchronously.",
        technical_reason="Too many distinct third-party domains were detected.",
        business_reason="Third parties add latency, privacy risk, and compliance surface.",
        category=RecommendationCategory.COMPLIANCE,
        effort=EffortLevel.MEDIUM,
        impact=ImpactLevel.MEDIUM,
        findings=("perf.network.too_many_third_party_domains", "biz.compliance.third_party_domains"),
        rules=("perf.network",),
    ),
)

# finding_id → template (built once; first registration wins for duplicates across templates).
FINDING_TO_TEMPLATE: dict[str, RecommendationTemplate] = {}
for _template in TEMPLATES:
    for _fid in _template.source_finding_ids:
        FINDING_TO_TEMPLATE.setdefault(_fid, _template)


@dataclass(frozen=True, slots=True)
class FallbackTemplateSpec:
    """Prefix-based fallback when no exact finding mapping exists."""

    prefix: str
    recommendation_id: str
    title: str
    description: str
    technical_reason: str
    business_reason: str
    category: RecommendationCategory
    effort: EffortLevel
    impact: ImpactLevel


FALLBACK_SPECS: tuple[FallbackTemplateSpec, ...] = (
    FallbackTemplateSpec(
        prefix="seo.",
        recommendation_id="rec.seo.generic_issue",
        title="Resolve SEO finding",
        description="Address the detected SEO issue using the related rule guidance.",
        technical_reason="An SEO finding was emitted without a specialized template.",
        business_reason="Unresolved SEO issues can weaken organic discovery.",
        category=RecommendationCategory.SEO,
        effort=EffortLevel.MEDIUM,
        impact=ImpactLevel.MEDIUM,
    ),
    FallbackTemplateSpec(
        prefix="a11y.",
        recommendation_id="rec.a11y.generic_issue",
        title="Resolve accessibility finding",
        description="Address the detected accessibility issue to improve inclusive access.",
        technical_reason="An accessibility finding was emitted without a specialized template.",
        business_reason="Accessibility gaps exclude users and increase compliance risk.",
        category=RecommendationCategory.ACCESSIBILITY,
        effort=EffortLevel.MEDIUM,
        impact=ImpactLevel.MEDIUM,
    ),
    FallbackTemplateSpec(
        prefix="sec.",
        recommendation_id="rec.sec.generic_issue",
        title="Resolve security finding",
        description="Address the detected security issue according to the related rule.",
        technical_reason="A security finding was emitted without a specialized template.",
        business_reason="Unresolved security gaps increase trust and breach risk.",
        category=RecommendationCategory.SECURITY,
        effort=EffortLevel.MEDIUM,
        impact=ImpactLevel.HIGH,
    ),
    FallbackTemplateSpec(
        prefix="perf.",
        recommendation_id="rec.perf.generic_issue",
        title="Resolve performance finding",
        description="Address the detected performance issue to improve load characteristics.",
        technical_reason="A performance finding was emitted without a specialized template.",
        business_reason="Slow experiences reduce engagement and conversion potential.",
        category=RecommendationCategory.PERFORMANCE,
        effort=EffortLevel.MEDIUM,
        impact=ImpactLevel.MEDIUM,
    ),
    FallbackTemplateSpec(
        prefix="biz.",
        recommendation_id="rec.business.generic_issue",
        title="Resolve business-impact finding",
        description="Address the underlying technical cause mapped by this business finding.",
        technical_reason="A business finding was emitted without a specialized template.",
        business_reason="Business-mapped issues highlight conversion, trust, or reach risk.",
        category=RecommendationCategory.BUSINESS,
        effort=EffortLevel.MEDIUM,
        impact=ImpactLevel.MEDIUM,
    ),
)


def resolve_template(finding_id: str) -> RecommendationTemplate:
    """Return the template for a finding_id (exact map, then prefix fallback)."""
    exact = FINDING_TO_TEMPLATE.get(finding_id)
    if exact is not None:
        return exact

    for spec in FALLBACK_SPECS:
        if finding_id.startswith(spec.prefix):
            return RecommendationTemplate(
                recommendation_id=f"{spec.recommendation_id}:{finding_id}",
                title=spec.title,
                description=spec.description,
                technical_reason=spec.technical_reason,
                business_reason=spec.business_reason,
                category=spec.category,
                estimated_effort=spec.effort,
                estimated_impact=spec.impact,
                related_rules=(finding_id,),
                source_finding_ids=(finding_id,),
                base_confidence=70,
            )

    return RecommendationTemplate(
        recommendation_id=f"rec.generic:{finding_id}",
        title="Resolve detected finding",
        description="Address the detected finding using the related technical rule.",
        technical_reason="Finding has no specialized or prefix template.",
        business_reason="Unresolved findings may affect quality, trust, or conversion.",
        category=RecommendationCategory.BUSINESS,
        estimated_effort=EffortLevel.MEDIUM,
        estimated_impact=ImpactLevel.MEDIUM,
        related_rules=(finding_id,),
        source_finding_ids=(finding_id,),
        base_confidence=60,
    )


def all_templates() -> tuple[RecommendationTemplate, ...]:
    return TEMPLATES

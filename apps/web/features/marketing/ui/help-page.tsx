import { ROUTES } from "@/shared/constants/routes";
import { Container, Section } from "@/shared/ui/layout";

import { HelpSearch, type HelpSection } from "./help-search";
import { MarketingCta } from "./marketing-cta";
import { MarketingShell } from "./marketing-shell";
import { PageHero } from "./page-hero";

const HELP_SECTIONS: readonly HelpSection[] = [
  {
    id: "getting-started",
    title: "Getting Started",
    summary: "Launch SitePilot and run your first website health check.",
    items: [
      "Open the home page or go directly to Analyze Website.",
      "Paste a public URL you are authorized to audit.",
      "Follow the analyzing flow until the report is ready.",
    ],
    links: [
      { label: "Analyze Website", href: ROUTES.audit },
      { label: "About SitePilot", href: ROUTES.about },
    ],
  },
  {
    id: "running-an-audit",
    title: "Running an Audit",
    summary: "Understand what happens after you submit a URL.",
    items: [
      "URL validation rejects unsafe or unreachable targets.",
      "Engines collect technical signals (SEO, performance, security, accessibility, and more).",
      "The report composer assembles scores and findings into one AuditReport.",
      "AI explanations are optional and run after the report exists.",
    ],
    links: [{ label: "Start an audit", href: ROUTES.audit }],
  },
  {
    id: "understanding-scores",
    title: "Understanding Scores",
    summary: "How category and overall health scores should be read.",
    items: [
      "Scores summarize automated observations — not guarantees.",
      "Category cards highlight where risk and opportunity concentrate.",
      "Severity and confidence help prioritize what to fix first.",
      "Re-run audits after changes to see movement over time.",
    ],
    links: [{ label: "FAQ: score calculation", href: `${ROUTES.faq}#scores` }],
  },
  {
    id: "ai-insights",
    title: "Understanding AI Insights",
    summary: "AI explains completed findings — it does not invent checks.",
    items: [
      "Generate explanations from report panels when AI is configured.",
      "Insights are grounded in existing findings and recommendations.",
      "AI is outside the audit pipeline and cannot change engine results.",
      "Always verify critical decisions against the underlying findings.",
    ],
    links: [
      { label: "FAQ: AI accuracy", href: `${ROUTES.faq}#ai-accuracy` },
      { label: "About grounded AI", href: `${ROUTES.about}#grounded-heading` },
    ],
  },
  {
    id: "sharing-reports",
    title: "Sharing Reports",
    summary: "Create a read-only link for stakeholders.",
    items: [
      "From a completed report, open Share → Copy Link or Open in New Tab.",
      "On mobile, native share is used when the browser supports it.",
      "Shared viewers cannot regenerate AI, export, or start new audits.",
      "Links use signed tokens and expire after a configured TTL.",
    ],
    links: [{ label: "FAQ: sharing", href: `${ROUTES.faq}#share` }],
  },
  {
    id: "exporting-reports",
    title: "Exporting Reports",
    summary: "Download PDF, JSON, or CSV from a completed report.",
    items: [
      "Use Export on the report page to download the format you need.",
      "Exports reuse the same composed report — no second report builder.",
      "Shared read-only views hide export controls by design.",
    ],
    links: [{ label: "FAQ: export", href: `${ROUTES.faq}#export` }],
  },
  {
    id: "troubleshooting",
    title: "Troubleshooting",
    summary: "Common recovery steps when something looks off.",
    items: [
      "Confirm the URL is public and correctly spelled (include https://).",
      "If analyzing stalls, refresh status or start a new audit.",
      "If AI fails, check provider configuration — audits still work without AI.",
      "Expired share links return Gone; create a new share from the owner report.",
    ],
    links: [{ label: "Contact support", href: ROUTES.contact }],
  },
  {
    id: "common-errors",
    title: "Common Errors",
    summary: "Messages you may see and what they usually mean.",
    items: [
      "Invalid URL / validation failed — target rejected by safety or format checks.",
      "Report not ready — audit still running or failed before composition.",
      "Share token invalid (404) — tampered or unknown token.",
      "Share token expired (410) — mint a fresh share link.",
    ],
    links: [{ label: "Contact", href: ROUTES.contact }],
  },
  {
    id: "keyboard",
    title: "Keyboard shortcuts",
    summary: "Accessibility-oriented navigation tips.",
    items: [
      "Tab / Shift+Tab move between interactive controls.",
      "Enter activates focused buttons and links.",
      "Escape closes drawers and dialogs where supported.",
      "Skip to content appears on focus for marketing pages.",
    ],
  },
] as const;

export function HelpPage() {
  return (
    <MarketingShell labelledBy="help-hero">
      <PageHero
        id="help-hero"
        eyebrow="Help Center"
        title="Documentation-style guidance for SitePilot"
        description="Search topics covering audits, scores, AI insights, sharing, export, and troubleshooting — without leaving the product design system."
      />

      <Section spacing="lg" aria-labelledby="help-topics-heading">
        <Container>
          <h2 id="help-topics-heading" className="sr-only">
            Help topics
          </h2>
          <HelpSearch sections={HELP_SECTIONS} />
        </Container>
      </Section>

      <MarketingCta
        title="Ready to try it?"
        description="Run an audit on a public site and explore the report with export and share."
        secondaryHref={ROUTES.faq}
        secondaryLabel="Read FAQ"
      />
    </MarketingShell>
  );
}

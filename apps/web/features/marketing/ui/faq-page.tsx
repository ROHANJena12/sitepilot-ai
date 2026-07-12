import Link from "next/link";

import { ROUTES } from "@/shared/constants/routes";
import { siteConfig } from "@/shared/config/site";
import { Container, Section } from "@/shared/ui/layout";
import { Text } from "@/shared/ui/typography";

import { FaqAccordion, type FaqItem } from "./faq-accordion";
import { MarketingCta } from "./marketing-cta";
import { MarketingShell } from "./marketing-shell";
import { PageHero } from "./page-hero";

const FAQ_ITEMS: readonly FaqItem[] = [
  {
    id: "what-is",
    question: "What is SitePilot?",
    answer: (
      <>
        {siteConfig.name} is an AI-powered website intelligence platform. It audits public
        sites for signals like SEO, performance, security, and accessibility, then composes a
        business-ready report with optional grounded AI explanations. Learn more on the{" "}
        <Link href={ROUTES.about} className="font-medium text-accent underline-offset-4 hover:underline">
          About
        </Link>{" "}
        page.
      </>
    ),
  },
  {
    id: "duration",
    question: "How long do audits take?",
    answer:
      "Most audits complete in minutes, depending on site size, network conditions, and engine workload. The analyzing screen shows progress while engines run and the report is composed.",
  },
  {
    id: "scores",
    question: "How are scores calculated?",
    answer:
      "Category and overall scores are derived from automated engine findings and scoring rules in the backend. They summarize observed issues at audit time — they are decision-support metrics, not guarantees of ranking, conversion, or compliance.",
  },
  {
    id: "ai-crawl",
    question: "Does AI crawl my website?",
    answer:
      "No. Dedicated audit engines crawl and analyze. AI is a separate explanation layer that runs after a report exists. It explains completed findings; it does not independently crawl or invent checks.",
  },
  {
    id: "export",
    question: "Can I export reports?",
    answer: (
      <>
        Yes. From a completed report, use Export to download PDF, JSON, or CSV. Exports reuse
        the same composed report used by the dashboard. Shared read-only links hide export
        controls. See the{" "}
        <Link href={ROUTES.help} className="font-medium text-accent underline-offset-4 hover:underline">
          Help Center
        </Link>
        .
      </>
    ),
  },
  {
    id: "share",
    question: "Can I share reports?",
    answer:
      "Yes. Share creates a signed, time-limited link. Recipients can view the report in read-only mode — they cannot regenerate AI, export, or trigger new audits.",
  },
  {
    id: "ai-accuracy",
    question: "How accurate are AI insights?",
    answer:
      "AI insights are grounded in completed audit artifacts, but language models can still be incomplete or imprecise. Treat explanations as assistive narrative. Verify important decisions against the underlying findings and your own expertise.",
  },
  {
    id: "data-storage",
    question: "How is my data stored?",
    answer: (
      <>
        Audit URLs and generated reports are stored so you can revisit, export, and share them.
        Operational logs support reliability and security. Details are in our{" "}
        <Link
          href={ROUTES.privacy}
          className="font-medium text-accent underline-offset-4 hover:underline"
        >
          Privacy Policy
        </Link>
        .
      </>
    ),
  },
];

export function FaqPage() {
  return (
    <MarketingShell labelledBy="faq-hero">
      <PageHero
        id="faq-hero"
        eyebrow="FAQ"
        title="Frequently asked questions"
        description="Straight answers about audits, scores, AI, sharing, export, and data."
      />

      <Section spacing="lg" aria-labelledby="faq-list-heading">
        <Container size="sm">
          <h2 id="faq-list-heading" className="sr-only">
            Frequently asked questions list
          </h2>
          <FaqAccordion items={FAQ_ITEMS} />
          <Text variant="muted" className="mt-8 text-center">
            Need more detail? Visit the{" "}
            <Link href={ROUTES.help} className="font-medium text-accent underline-offset-4 hover:underline">
              Help Center
            </Link>{" "}
            or{" "}
            <Link
              href={ROUTES.contact}
              className="font-medium text-accent underline-offset-4 hover:underline"
            >
              Contact
            </Link>
            .
          </Text>
        </Container>
      </Section>

      <MarketingCta secondaryHref={ROUTES.help} secondaryLabel="Help Center" />
    </MarketingShell>
  );
}

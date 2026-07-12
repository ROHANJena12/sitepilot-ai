import Link from "next/link";
import {
  Bot,
  Layers,
  Lock,
  Map,
  Radar,
  Sparkles,
  Workflow,
} from "lucide-react";

import { ROUTES } from "@/shared/constants/routes";
import { siteConfig } from "@/shared/config/site";
import { Reveal } from "@/shared/ui/motion";
import { Badge } from "@/shared/ui/feedback";
import { Card, CardContent, CardHeader, CardTitle } from "@/shared/ui/cards";
import { Container, Section } from "@/shared/ui/layout";
import { Heading, Text } from "@/shared/ui/typography";

import { MarketingCta } from "./marketing-cta";
import { MarketingShell } from "./marketing-shell";
import { PageHero } from "./page-hero";

const HOW_STEPS = [
  {
    title: "Validate & crawl safely",
    body: "Public URLs are validated against SSRF-safe rules before engines begin work.",
  },
  {
    title: "Run specialized engines",
    body: "SEO, performance, security, accessibility, and related signals are collected as technical truth.",
  },
  {
    title: "Compose a business report",
    body: "Scores, findings, and impact are assembled into one AuditReport — never invented after the fact.",
  },
  {
    title: "Explain with grounded AI",
    body: "AI explains completed findings only. It does not invent checks or alter engine results.",
  },
] as const;

const STACK = [
  "Next.js App Router + Feature-Sliced Design",
  "FastAPI Clean / Hexagonal backend",
  "PostgreSQL as system of record",
  "Engine pipeline with typed results",
  "Multi-provider AI explanation layer",
  "Signed read-only share links",
] as const;

const ROADMAP = [
  {
    label: "Now",
    items: ["Live audits", "Grounded AI insights", "Export & share"],
  },
  {
    label: "Next",
    items: ["Deeper help content", "Team workspaces", "Richer history"],
  },
  {
    label: "Later",
    items: ["Scheduled monitoring", "Integrations", "Governance controls"],
  },
] as const;

export function AboutPage() {
  return (
    <MarketingShell labelledBy="about-hero">
      <PageHero
        id="about-hero"
        eyebrow="About"
        title={`What is ${siteConfig.name}?`}
        description="SitePilot turns crawl data, performance signals, SEO insights, and accessibility findings into a business-ready health report — with AI that explains what to fix first."
      />

      <Section spacing="lg" aria-labelledby="mission-heading">
        <Container className="grid gap-10 lg:grid-cols-[1.1fr_0.9fr] lg:items-start">
          <Reveal>
            <Heading id="mission-heading" level="h2">
              Mission
            </Heading>
            <Text variant="muted" className="mt-4 text-base">
              Help product, marketing, and engineering ship better web experiences
              without drowning in raw technical dumps. SitePilot exists to make website
              health understandable, prioritized, and actionable.
            </Text>
            <Text variant="muted" className="mt-4">
              We believe audits should produce decisions — not just scores. Every
              recommendation should answer what is wrong, why it matters, and what to do next.
            </Text>
          </Reveal>
          <Reveal delay={0.06}>
            <Card className="border-accent/25 bg-accent-muted/30">
              <CardHeader>
                <Badge variant="accent" className="w-fit">
                  Design principle
                </Badge>
                <CardTitle>Explain, never invent</CardTitle>
              </CardHeader>
              <CardContent>
                <Text variant="muted">
                  AI is a presentation layer on top of completed audit artifacts. Engines
                  produce truth. The report composer assembles it. AI explains it —
                  without crawling, scoring, or rewriting findings.
                </Text>
              </CardContent>
            </Card>
          </Reveal>
        </Container>
      </Section>

      <Section
        spacing="lg"
        className="border-y border-border bg-bg-subtle"
        aria-labelledby="how-heading"
      >
        <Container>
          <Reveal className="mx-auto max-w-2xl text-center">
            <Heading id="how-heading" level="h2">
              How SitePilot works
            </Heading>
            <Text variant="muted" className="mt-3">
              A clear pipeline from URL to prioritized action.
            </Text>
          </Reveal>
          <ol className="mt-12 grid gap-4 md:grid-cols-2">
            {HOW_STEPS.map((step, index) => (
              <li key={step.title}>
                <Reveal delay={index * 0.05}>
                  <Card className="h-full">
                    <CardHeader>
                      <p className="font-mono text-xs text-accent">
                        {String(index + 1).padStart(2, "0")}
                      </p>
                      <CardTitle>{step.title}</CardTitle>
                    </CardHeader>
                    <CardContent>
                      <Text variant="muted">{step.body}</Text>
                    </CardContent>
                  </Card>
                </Reveal>
              </li>
            ))}
          </ol>
        </Container>
      </Section>

      <Section spacing="lg" aria-labelledby="architecture-heading">
        <Container>
          <Reveal className="mx-auto max-w-2xl text-center">
            <Heading id="architecture-heading" level="h2">
              Architecture overview
            </Heading>
            <Text variant="muted" className="mt-3">
              Clean boundaries keep audits trustworthy and the product maintainable.
            </Text>
          </Reveal>
          <div className="mt-12 grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
            {[
              {
                icon: Workflow,
                title: "Audit pipeline",
                body: "Orchestrates engines with typed results. No silent invention of findings.",
              },
              {
                icon: Layers,
                title: "Report composer",
                body: "Single assembly path into AuditReportDTO — shared by dashboard, export, and share.",
              },
              {
                icon: Bot,
                title: "AIService",
                body: "Optional explanations for completed artifacts only. Outside the audit pipeline.",
              },
              {
                icon: Radar,
                title: "Engines",
                body: "Specialized checks for SEO, performance, security, accessibility, and more.",
              },
              {
                icon: Lock,
                title: "Secure sharing",
                body: "HMAC-signed, time-limited tokens for read-only report links — no DB share table.",
              },
              {
                icon: Sparkles,
                title: "Grounded insights",
                body: "AI sees findings that already exist. It cannot invent checks or change scores.",
              },
            ].map((item, index) => (
              <Reveal key={item.title} delay={index * 0.04}>
                <Card className="h-full">
                  <CardHeader>
                    <item.icon className="h-5 w-5 text-accent" aria-hidden />
                    <CardTitle className="text-base">{item.title}</CardTitle>
                  </CardHeader>
                  <CardContent>
                    <Text variant="muted">{item.body}</Text>
                  </CardContent>
                </Card>
              </Reveal>
            ))}
          </div>
        </Container>
      </Section>

      <Section
        spacing="lg"
        className="border-y border-border bg-bg-subtle"
        aria-labelledby="stack-heading"
      >
        <Container className="grid gap-10 lg:grid-cols-2 lg:items-start">
          <Reveal>
            <Heading id="stack-heading" level="h2">
              Technology stack
            </Heading>
            <Text variant="muted" className="mt-3">
              Built as an enterprise monorepo for production SaaS delivery.
            </Text>
            <ul className="mt-6 space-y-3">
              {STACK.map((item) => (
                <li key={item} className="flex gap-3 text-sm text-foreground">
                  <span className="mt-2 h-1.5 w-1.5 shrink-0 rounded-full bg-accent" aria-hidden />
                  {item}
                </li>
              ))}
            </ul>
          </Reveal>
          <Reveal delay={0.06}>
            <Heading id="grounded-heading" level="h2">
              Why AI explanations are grounded
            </Heading>
            <Text variant="muted" className="mt-3">
              SitePilot separates measurement from narrative. Engines measure. The composer
              assembles. AI explains. That separation is intentional:
            </Text>
            <ul className="mt-6 space-y-3 text-sm text-foreground-muted">
              <li>
                <strong className="text-foreground">No pipeline injection</strong> — AI is not an
                audit engine and does not alter crawl results.
              </li>
              <li>
                <strong className="text-foreground">Completed artifacts only</strong> — prompts are
                grounded in findings that already exist in the report.
              </li>
              <li>
                <strong className="text-foreground">Transparent fallbacks</strong> — provider
                routing can fall back, but never invents missing evidence.
              </li>
            </ul>
          </Reveal>
        </Container>
      </Section>

      <Section spacing="lg" aria-labelledby="roadmap-heading">
        <Container>
          <Reveal className="mx-auto max-w-2xl text-center">
            <div className="mb-3 inline-flex items-center gap-2 text-accent">
              <Map className="h-4 w-4" aria-hidden />
              <span className="text-xs font-medium uppercase tracking-[0.14em]">Roadmap</span>
            </div>
            <Heading id="roadmap-heading" level="h2">
              Where we are headed
            </Heading>
            <Text variant="muted" className="mt-3">
              Directional themes — not delivery commitments.
            </Text>
          </Reveal>
          <div className="mt-12 grid gap-4 md:grid-cols-3">
            {ROADMAP.map((column, index) => (
              <Reveal key={column.label} delay={index * 0.05}>
                <Card className="h-full">
                  <CardHeader>
                    <Badge variant="neutral" className="w-fit">
                      {column.label}
                    </Badge>
                    <CardTitle className="sr-only">{column.label} themes</CardTitle>
                  </CardHeader>
                  <CardContent>
                    <ul className="space-y-2.5">
                      {column.items.map((item) => (
                        <li key={item} className="text-sm text-foreground-muted">
                          {item}
                        </li>
                      ))}
                    </ul>
                  </CardContent>
                </Card>
              </Reveal>
            ))}
          </div>
          <Text variant="muted" className="mx-auto mt-10 max-w-2xl text-center">
            Open source transparency: follow development on{" "}
            <a
              href={siteConfig.links.github}
              target="_blank"
              rel="noopener noreferrer"
              className="font-medium text-accent underline-offset-4 hover:underline"
            >
              GitHub
            </a>
            . Architecture details live in{" "}
            <Link
              href={ROUTES.help}
              className="font-medium text-accent underline-offset-4 hover:underline"
            >
              Help Center
            </Link>
            .
          </Text>
        </Container>
      </Section>

      <MarketingCta
        title="See SitePilot on your site"
        description="Run a live audit and get a prioritized report with grounded AI explanations."
      />
    </MarketingShell>
  );
}

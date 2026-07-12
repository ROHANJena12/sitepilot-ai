import {
  Gauge,
  Lock,
  PersonStanding,
  Search,
  Sparkles,
  LineChart,
} from "lucide-react";

import { Reveal } from "@/shared/ui/motion";
import { Card, CardHeader, CardTitle, CardDescription } from "@/shared/ui/cards";
import { Container, Section } from "@/shared/ui/layout";
import { Heading, Text } from "@/shared/ui/typography";

const FEATURES = [
  {
    title: "SEO Analysis",
    description:
      "Surface metadata gaps, structure issues, and crawlability problems before they cost rankings.",
    icon: Search,
  },
  {
    title: "Performance",
    description:
      "Translate Core Web Vitals into plain language — what slows the page and what to fix first.",
    icon: Gauge,
  },
  {
    title: "Security",
    description:
      "Check headers, TLS posture, and common exposure risks with evidence you can hand to engineering.",
    icon: Lock,
  },
  {
    title: "Accessibility",
    description:
      "Catch WCAG-aligned issues early so your product works for more people — and passes audits.",
    icon: PersonStanding,
  },
  {
    title: "AI Recommendations",
    description:
      "Every finding comes with a recommended action, effort cue, and confidence — not a raw dump.",
    icon: Sparkles,
  },
  {
    title: "Business Impact",
    description:
      "Connect technical debt to outcomes: conversion risk, brand trust, and prioritization ROI.",
    icon: LineChart,
  },
] as const;

export function LandingFeatures() {
  return (
    <Section id="features" spacing="lg" aria-labelledby="features-heading">
      <Container>
        <Reveal className="mx-auto max-w-2xl text-center">
          <Heading id="features-heading" level="h2">
            Everything that matters, in one pass
          </Heading>
          <Text variant="muted" className="mt-3">
            Six lenses. One report. Built for founders, agencies, and operators who need decisions —
            not dashboards of noise.
          </Text>
        </Reveal>

        <ul className="mt-12 grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
          {FEATURES.map((feature, index) => {
            const Icon = feature.icon;
            return (
              <li key={feature.title} className="h-full">
                <Reveal delay={0.03 * Math.min(index, 4)} className="h-full">
                  <Card className="h-full transition-colors duration-fast hover:bg-surface-hover">
                    <CardHeader>
                      <span className="mb-3 inline-flex h-10 w-10 items-center justify-center rounded-md bg-accent-muted text-accent">
                        <Icon className="h-5 w-5" aria-hidden />
                      </span>
                      <CardTitle className="text-base">{feature.title}</CardTitle>
                      <CardDescription className="text-sm leading-relaxed">
                        {feature.description}
                      </CardDescription>
                    </CardHeader>
                  </Card>
                </Reveal>
              </li>
            );
          })}
        </ul>
      </Container>
    </Section>
  );
}

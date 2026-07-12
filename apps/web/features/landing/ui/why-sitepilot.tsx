import { Check, X } from "lucide-react";

import { Reveal } from "@/shared/ui/motion";
import { Badge } from "@/shared/ui/feedback";
import { Card, CardContent, CardHeader, CardTitle } from "@/shared/ui/cards";
import { Container, Section } from "@/shared/ui/layout";
import { Heading, Text } from "@/shared/ui/typography";

const TRADITIONAL = [
  "Raw technical scores without context",
  "Developer-only jargon",
  "No clear priority order",
  "Little guidance on business impact",
] as const;

const SITEPILOT = [
  "Findings explained in business language",
  "Severity + confidence on every issue",
  "AI recommendations with effort cues",
  "Impact-aware prioritization",
] as const;

export function WhySitePilot() {
  return (
    <Section id="why" spacing="lg" aria-labelledby="why-heading">
      <Container>
        <Reveal className="mx-auto max-w-2xl text-center">
          <Heading id="why-heading" level="h2">
            Why SitePilot AI
          </Heading>
          <Text variant="muted" className="mt-3">
            Traditional audits tell you something is wrong. SitePilot tells you what to do about it.
          </Text>
        </Reveal>

        <div className="mt-12 grid gap-4 md:grid-cols-2">
          <Reveal>
            <Card className="h-full border-border/80 bg-surface/50">
              <CardHeader>
                <Badge variant="neutral" className="w-fit">
                  Traditional website audit
                </Badge>
                <CardTitle className="text-lg">Score dumps & noise</CardTitle>
              </CardHeader>
              <CardContent>
                <ul className="space-y-3">
                  {TRADITIONAL.map((item) => (
                    <li key={item} className="flex gap-3 text-sm text-foreground-muted">
                      <X className="mt-0.5 h-4 w-4 shrink-0 text-danger" aria-hidden />
                      <span>{item}</span>
                    </li>
                  ))}
                </ul>
              </CardContent>
            </Card>
          </Reveal>

          <Reveal delay={0.08}>
            <Card className="h-full border-accent/30 bg-accent-muted/40 shadow-md">
              <CardHeader>
                <Badge variant="accent" className="w-fit">
                  SitePilot AI
                </Badge>
                <CardTitle className="text-lg">Intelligence you can act on</CardTitle>
              </CardHeader>
              <CardContent>
                <ul className="space-y-3">
                  {SITEPILOT.map((item) => (
                    <li key={item} className="flex gap-3 text-sm text-foreground">
                      <Check className="mt-0.5 h-4 w-4 shrink-0 text-accent" aria-hidden />
                      <span>{item}</span>
                    </li>
                  ))}
                </ul>
              </CardContent>
            </Card>
          </Reveal>
        </div>
      </Container>
    </Section>
  );
}

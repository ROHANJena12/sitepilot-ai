"use client";

import { Reveal } from "@/shared/ui/motion";
import { Card, CardContent, CardHeader } from "@/shared/ui/cards";
import { Heading, Text } from "@/shared/ui/typography";

type ExecutiveSummaryProps = {
  bullets: string[];
  subtitle?: string;
};

export function ExecutiveSummary({
  bullets,
  subtitle = "Pipeline summary of this audit — concise signals from deterministic engines.",
}: ExecutiveSummaryProps) {
  return (
    <Reveal>
      <section aria-labelledby="summary-heading">
        <Card className="border-border/80 bg-surface/90">
          <CardHeader>
            <Heading id="summary-heading" level="h2" className="text-lg md:text-xl">
              Executive summary
            </Heading>
            <Text variant="muted" className="mt-1">
              {subtitle}
            </Text>
          </CardHeader>
          <CardContent>
            <ul className="space-y-2.5">
              {bullets.map((item) => (
                <li
                  key={item.slice(0, 64)}
                  className="flex gap-3 text-sm leading-relaxed text-foreground-muted"
                >
                  <span className="mt-2 h-1.5 w-1.5 shrink-0 rounded-pill bg-accent" aria-hidden />
                  <span>{item}</span>
                </li>
              ))}
            </ul>
          </CardContent>
        </Card>
      </section>
    </Reveal>
  );
}

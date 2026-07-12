"use client";

import { Reveal } from "@/shared/ui/motion";
import { HealthScoreRing } from "@/shared/ui/charts";
import { Badge } from "@/shared/ui/feedback";
import { Card, CardContent } from "@/shared/ui/cards";
import { Heading, Text } from "@/shared/ui/typography";

type OverallHealthProps = {
  score: number;
  host: string;
};

export function OverallHealth({ score, host }: OverallHealthProps) {
  return (
    <Reveal delay={0.05}>
      <section aria-labelledby="health-heading">
        <Card className="overflow-hidden border-accent/20 bg-[radial-gradient(ellipse_at_top,var(--color-accent-muted),var(--color-surface)_55%)]">
          <CardContent className="flex flex-col items-center gap-6 px-6 py-10 text-center sm:flex-row sm:justify-between sm:text-left md:px-10 md:py-12">
            <div className="max-w-md space-y-3">
              <Badge variant="accent" className="w-fit">
                Overall Health
              </Badge>
              <Heading id="health-heading" level="h2" className="text-2xl md:text-3xl">
                {host} scores {score}/100
              </Heading>
              <Text variant="muted">
                A composite view across SEO, performance, security, accessibility, and
                business-ready prioritization.
              </Text>
            </div>
            <HealthScoreRing
              value={score}
              size="xl"
              label={`Overall health score ${score} of 100`}
            />
          </CardContent>
        </Card>
      </section>
    </Reveal>
  );
}

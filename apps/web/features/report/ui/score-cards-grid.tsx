"use client";

import { Reveal } from "@/shared/ui/motion";
import { ScoreCard } from "@/shared/ui/cards";
import { Heading, Text } from "@/shared/ui/typography";
import type { ReportDashboardView } from "../model/map-api-report";

type ScoreCardsGridProps = {
  scores: ReportDashboardView["scores"];
};

export function ScoreCardsGrid({ scores }: ScoreCardsGridProps) {
  return (
    <section aria-labelledby="scores-heading" className="space-y-6">
      <Reveal>
        <div>
          <Heading id="scores-heading" level="h2" className="text-lg md:text-xl">
            Score cards
          </Heading>
          <Text variant="muted" className="mt-1">
            Category health across the audit engines.
          </Text>
        </div>
      </Reveal>
      <ul className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
        {scores.map((score, index) => (
          <li key={score.label}>
              <Reveal delay={0.03 * Math.min(index, 4)} className="h-full">
              <ScoreCard
                label={score.label}
                value={score.value}
                description={score.description}
                size="sm"
                className="h-full"
              />
            </Reveal>
          </li>
        ))}
      </ul>
    </section>
  );
}

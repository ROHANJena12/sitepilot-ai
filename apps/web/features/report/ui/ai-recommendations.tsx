"use client";

import type { ReactNode } from "react";
import { Reveal } from "@/shared/ui/motion";
import { RecommendationCard } from "@/shared/ui/cards";
import { Heading, Text } from "@/shared/ui/typography";
import type { ReportDashboardView } from "../model/map-api-report";

type Rec = ReportDashboardView["recommendations"][number];

type AiRecommendationsProps = {
  recommendations: Rec[];
  heading?: string;
  subtitle?: string;
  renderAi?: (rec: Rec) => ReactNode;
};

/**
 * Recommendations & Quick Wins — responsive CSS Grid with equal row heights.
 * Grid items stretch; each card is a flex column with the AI footer pinned bottom.
 */
export function AiRecommendations({
  recommendations,
  heading = "Recommendations",
  subtitle = "Suggested actions ranked by priority and expected impact.",
  renderAi,
}: AiRecommendationsProps) {
  if (!recommendations.length) {
    return (
      <section className="space-y-3">
        <Heading level="h2" className="text-lg md:text-xl">
          {heading}
        </Heading>
        <Text variant="muted">No recommendations for this audit.</Text>
      </section>
    );
  }

  return (
    <section aria-labelledby="recs-heading" className="space-y-6">
      <Reveal>
        <div>
          <Heading id="recs-heading" level="h2" className="text-lg md:text-xl">
            {heading}
          </Heading>
          <Text variant="muted" className="mt-1 max-w-2xl">
            {subtitle}
          </Text>
        </div>
      </Reveal>
      <ul className="m-0 grid list-none grid-cols-1 items-stretch gap-6 p-0 md:grid-cols-2 xl:grid-cols-3">
        {recommendations.map((rec, index) => (
          <li key={rec.id} className="flex min-w-0">
            <Reveal delay={0.04 * Math.min(index, 5)} className="flex h-full w-full min-w-0">
              <RecommendationCard
                className="w-full"
                title={rec.title}
                priority={rec.priority}
                difficulty={rec.difficulty}
                estimatedImprovement={rec.estimatedImprovement}
                expectedImpact={rec.expectedImpact}
                confidence={rec.confidence}
              >
                {renderAi?.(rec)}
              </RecommendationCard>
            </Reveal>
          </li>
        ))}
      </ul>
    </section>
  );
}

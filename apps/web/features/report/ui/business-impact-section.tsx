"use client";

import {
  DollarSign,
  Search,
  ShieldCheck,
  TrendingUp,
  Sparkles,
} from "lucide-react";

import { Reveal } from "@/shared/ui/motion";
import { BusinessImpactCard } from "@/shared/ui/cards";
import { Heading, Text } from "@/shared/ui/typography";
import type { ReportDashboardView } from "../model/map-api-report";

const ICONS = {
  Revenue: DollarSign,
  SEO: Search,
  Trust: ShieldCheck,
  Conversion: TrendingUp,
  Brand: Sparkles,
} as const;

type BusinessImpactSectionProps = {
  items: ReportDashboardView["businessImpact"];
};

export function BusinessImpactSection({ items }: BusinessImpactSectionProps) {
  return (
    <section aria-labelledby="impact-heading" className="space-y-6">
      <Reveal>
        <div>
          <Heading id="impact-heading" level="h2" className="text-lg md:text-xl">
            Business impact
          </Heading>
          <Text variant="muted" className="mt-1">
            How technical findings map to revenue, trust, and brand outcomes.
          </Text>
        </div>
      </Reveal>
      {items.length === 0 ? (
        <Text variant="muted" className="rounded-lg border border-border bg-surface px-4 py-8 text-center text-sm">
          No business-impact summaries were produced for this report.
        </Text>
      ) : (
      <ul className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-5">
        {items.map((item, index) => {
          const Icon = ICONS[item.domain as keyof typeof ICONS] ?? Sparkles;
          return (
            <li key={`${item.domain}-${index}`} className="h-full">
              <Reveal delay={0.04 * index} className="h-full">
                <BusinessImpactCard
                  domain={item.domain}
                  signal={item.signal}
                  statement={item.statement}
                  icon={<Icon className="h-4 w-4" aria-hidden />}
                />
              </Reveal>
            </li>
          );
        })}
      </ul>
      )}
    </section>
  );
}

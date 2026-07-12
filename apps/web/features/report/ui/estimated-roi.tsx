"use client";

import { Reveal } from "@/shared/ui/motion";
import { Badge } from "@/shared/ui/feedback";
import { Card, CardContent, CardHeader } from "@/shared/ui/cards";
import { Heading, Text } from "@/shared/ui/typography";
import type { ReportDashboardView } from "../model/map-api-report";

type EstimatedRoiProps = {
  roi: ReportDashboardView["roi"];
};

const toneBadge = {
  success: "success",
  warning: "warning",
  accent: "accent",
} as const;

export function EstimatedRoi({ roi }: EstimatedRoiProps) {
  return (
    <Reveal>
      <section aria-labelledby="roi-heading">
        <Card className="border-accent/25 bg-accent-muted/30">
          <CardHeader className="space-y-2">
            <Badge variant="accent" className="w-fit">
              {roi.band}
            </Badge>
            <Heading id="roi-heading" level="h2" className="text-lg md:text-xl">
              {roi.headline}
            </Heading>
            <Text variant="muted">{roi.summary}</Text>
          </CardHeader>
          <CardContent>
            <ul className="grid gap-3 sm:grid-cols-3">
              {roi.items.map((item) => (
                <li
                  key={item.label}
                  className="rounded-lg border border-border bg-surface/80 px-4 py-3"
                >
                  <p className="text-xs text-foreground-subtle">{item.label}</p>
                  <div className="mt-2 flex items-center justify-between gap-2">
                    <p className="text-sm font-semibold text-foreground">{item.value}</p>
                    <Badge variant={toneBadge[item.tone]} size="sm">
                      {item.tone === "success"
                        ? "High"
                        : item.tone === "warning"
                          ? "Plan"
                          : "Lift"}
                    </Badge>
                  </div>
                </li>
              ))}
            </ul>
          </CardContent>
        </Card>
      </section>
    </Reveal>
  );
}

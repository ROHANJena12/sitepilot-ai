"use client";

import * as React from "react";
import { useReducedMotion } from "framer-motion";
import {
  Bar,
  BarChart,
  CartesianGrid,
  Cell,
  Pie,
  PieChart,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";

import { ANIMATIONS } from "@/shared/constants/animations";
import { Reveal } from "@/shared/ui/motion";
import { ChartContainer, chartTokens } from "@/shared/ui/charts";
import { Card, CardContent, CardHeader } from "@/shared/ui/cards";
import { Heading, Text } from "@/shared/ui/typography";
import type { ReportDashboardView } from "../model/map-api-report";

type ReportChartsProps = {
  charts: ReportDashboardView["charts"];
};

const severityColors = [
  chartTokens.danger,
  chartTokens.warning,
  chartTokens.scoreMid,
  chartTokens.success,
];

const CHART_HEIGHT = 240;

function ChartCard({
  title,
  description,
  children,
  delay = 0,
}: {
  title: string;
  description: string;
  children: React.ReactNode;
  delay?: number;
}) {
  return (
    <Reveal delay={delay} className="h-full">
      <Card className="h-full">
        <CardHeader className="pb-2">
          <Heading level="h3" className="text-base">
            {title}
          </Heading>
          <Text variant="caption">{description}</Text>
        </CardHeader>
        <CardContent>{children}</CardContent>
      </Card>
    </Reveal>
  );
}

export function ReportCharts({ charts }: ReportChartsProps) {
  const reduceMotion = useReducedMotion();
  const animationDuration = reduceMotion ? 0 : ANIMATIONS.score;

  const healthData = React.useMemo(
    () => charts.healthDistribution,
    [charts.healthDistribution],
  );
  const severityData = React.useMemo(
    () => charts.issueSeverity,
    [charts.issueSeverity],
  );
  const performanceData = React.useMemo(
    () => charts.performanceBreakdown,
    [charts.performanceBreakdown],
  );

  return (
    <section aria-labelledby="charts-heading" className="space-y-6">
      <Reveal>
        <div>
          <Heading id="charts-heading" level="h2" className="text-lg md:text-xl">
            Charts
          </Heading>
          <Text variant="muted" className="mt-1">
            Visualizations from this audit report.
          </Text>
        </div>
      </Reveal>

      <div className="grid gap-4 lg:grid-cols-3">
        <ChartCard
          title="Health distribution"
          description="Category scores across engines"
          delay={0.04}
        >
          <div aria-hidden>
            <ChartContainer minHeight={CHART_HEIGHT} height={CHART_HEIGHT}>
              <BarChart
                data={healthData}
                margin={{ top: 8, right: 4, left: -18, bottom: 0 }}
              >
                <CartesianGrid stroke={chartTokens.border} vertical={false} strokeDasharray="3 3" />
                <XAxis dataKey="name" tickLine={false} axisLine={false} fontSize={11} />
                <YAxis domain={[0, 100]} tickLine={false} axisLine={false} fontSize={11} />
                <Tooltip
                  cursor={{ fill: "var(--color-surface-hover)" }}
                  contentStyle={{
                    background: "var(--color-surface)",
                    border: "1px solid var(--color-border)",
                    borderRadius: "var(--radius-md)",
                    color: "var(--color-text)",
                  }}
                />
                <Bar
                  dataKey="score"
                  fill={chartTokens.accent}
                  radius={[6, 6, 0, 0]}
                  animationDuration={animationDuration}
                  isAnimationActive={!reduceMotion}
                />
              </BarChart>
            </ChartContainer>
          </div>
          <ul className="sr-only">
            {healthData.map((item) => (
              <li key={item.name}>
                {item.name}: {item.score}
              </li>
            ))}
          </ul>
        </ChartCard>

        <ChartCard
          title="Issue severity"
          description="Count of findings by severity"
          delay={0.06}
        >
          <div aria-hidden>
            <ChartContainer minHeight={CHART_HEIGHT} height={CHART_HEIGHT}>
              <PieChart>
                <Pie
                  data={severityData}
                  dataKey="count"
                  nameKey="name"
                  innerRadius={54}
                  outerRadius={82}
                  paddingAngle={3}
                  animationDuration={animationDuration}
                  isAnimationActive={!reduceMotion}
                >
                  {severityData.map((entry, index) => (
                    <Cell
                      key={entry.name}
                      fill={severityColors[index % severityColors.length]}
                    />
                  ))}
                </Pie>
                <Tooltip
                  contentStyle={{
                    background: "var(--color-surface)",
                    border: "1px solid var(--color-border)",
                    borderRadius: "var(--radius-md)",
                    color: "var(--color-text)",
                  }}
                />
              </PieChart>
            </ChartContainer>
          </div>
          <ul className="mt-2 flex flex-wrap justify-center gap-3 text-xs text-foreground-muted">
            {severityData.map((item, index) => (
              <li key={item.name} className="inline-flex items-center gap-1.5">
                <span
                  className="h-2 w-2 rounded-pill"
                  style={{ background: severityColors[index % severityColors.length] }}
                  aria-hidden
                />
                {item.name} ({item.count})
              </li>
            ))}
          </ul>
        </ChartCard>

        <ChartCard
          title="Performance breakdown"
          description="Category performance signals from this report"
          delay={0.08}
        >
          {performanceData.length === 0 ? (
            <Text variant="muted" className="py-10 text-center text-sm">
              No performance breakdown data for this report.
            </Text>
          ) : (
            <>
          <div aria-hidden>
            <ChartContainer minHeight={CHART_HEIGHT} height={CHART_HEIGHT}>
              <BarChart
                layout="vertical"
                data={performanceData}
                margin={{ top: 8, right: 12, left: 8, bottom: 0 }}
              >
                <CartesianGrid stroke={chartTokens.border} horizontal={false} strokeDasharray="3 3" />
                <XAxis type="number" domain={[0, 100]} hide />
                <YAxis
                  type="category"
                  dataKey="name"
                  tickLine={false}
                  axisLine={false}
                  width={48}
                  fontSize={11}
                />
                <Tooltip
                  cursor={{ fill: "var(--color-surface-hover)" }}
                  contentStyle={{
                    background: "var(--color-surface)",
                    border: "1px solid var(--color-border)",
                    borderRadius: "var(--radius-md)",
                    color: "var(--color-text)",
                  }}
                />
                <Bar
                  dataKey="value"
                  fill={chartTokens.info}
                  radius={[0, 6, 6, 0]}
                  animationDuration={animationDuration}
                  isAnimationActive={!reduceMotion}
                />
              </BarChart>
            </ChartContainer>
          </div>
          <ul className="sr-only">
            {performanceData.map((item) => (
              <li key={item.name}>
                {item.name}: {item.value}
              </li>
            ))}
          </ul>
            </>
          )}
        </ChartCard>
      </div>
    </section>
  );
}

export const ReportChartsMemo = React.memo(ReportCharts);

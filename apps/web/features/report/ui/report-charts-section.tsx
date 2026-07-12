"use client";

import dynamic from "next/dynamic";

import { Skeleton } from "@/shared/ui/feedback";
import type { ReportDashboardView } from "../model/map-api-report";

const ReportChartsLazy = dynamic(
  () =>
    import("./report-charts").then((mod) => ({
      default: mod.ReportChartsMemo,
    })),
  {
    ssr: false,
    loading: () => (
      <div className="space-y-4" aria-busy="true" aria-label="Loading charts">
        <Skeleton className="h-8 w-40" />
        <div className="grid gap-4 lg:grid-cols-3">
          <Skeleton className="h-64 rounded-lg" />
          <Skeleton className="h-64 rounded-lg" />
          <Skeleton className="h-64 rounded-lg" />
        </div>
      </div>
    ),
  },
);

type Props = {
  charts: ReportDashboardView["charts"];
};

/** Code-split Recharts off the critical report path. */
export function ReportChartsSection({ charts }: Props) {
  return <ReportChartsLazy charts={charts} />;
}

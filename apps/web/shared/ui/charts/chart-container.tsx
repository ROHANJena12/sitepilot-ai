"use client";

import * as React from "react";
import {
  ResponsiveContainer,
  type ResponsiveContainerProps,
} from "recharts";

import { cn } from "@/shared/lib/utils";

/**
 * Token-aware chart shell. Pass Recharts children; colors should use CSS vars
 * via Tailwind classes or `var(--color-*)` / `var(--score-*)` in series props.
 */
export type ChartContainerProps = {
  className?: string;
  children: ResponsiveContainerProps["children"];
  height?: number | string;
  minHeight?: number;
};

export function ChartContainer({
  className,
  children,
  height = "100%",
  minHeight = 200,
}: ChartContainerProps) {
  return (
    <div
      className={cn("w-full text-foreground-muted [&_.recharts-cartesian-axis-tick_text]:fill-current", className)}
      style={{ height, minHeight }}
    >
      <ResponsiveContainer width="100%" height="100%">
        {children}
      </ResponsiveContainer>
    </div>
  );
}

/** Semantic chart color tokens for series / legends (no hex in call sites). */
export const chartTokens = {
  accent: "var(--color-accent)",
  success: "var(--color-success)",
  warning: "var(--color-warning)",
  danger: "var(--color-danger)",
  info: "var(--color-info)",
  muted: "var(--color-text-muted)",
  border: "var(--color-border)",
  scoreGood: "var(--score-good)",
  scoreMid: "var(--score-mid)",
  scorePoor: "var(--score-poor)",
} as const;

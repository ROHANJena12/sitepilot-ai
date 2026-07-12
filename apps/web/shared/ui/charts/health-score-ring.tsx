"use client";

import * as React from "react";
import { cva, type VariantProps } from "class-variance-authority";

import { cn } from "@/shared/lib/utils";

function scoreTone(value: number, max: number): "good" | "mid" | "poor" {
  const ratio = max === 0 ? 0 : value / max;
  if (ratio >= 0.8) return "good";
  if (ratio >= 0.5) return "mid";
  return "poor";
}

const sizeMap = {
  sm: { box: 72, stroke: 6, valueClass: "text-lg" },
  md: { box: 112, stroke: 8, valueClass: "text-2xl" },
  lg: { box: 148, stroke: 10, valueClass: "text-3xl" },
  xl: { box: 188, stroke: 12, valueClass: "text-4xl" },
} as const;

const ringToneClass = cva("", {
  variants: {
    tone: {
      good: "stroke-score-good",
      mid: "stroke-score-mid",
      poor: "stroke-score-poor",
    },
  },
  defaultVariants: {
    tone: "mid",
  },
});

export type HealthScoreRingProps = React.HTMLAttributes<HTMLDivElement> & {
  value: number;
  max?: number;
  size?: keyof typeof sizeMap;
  label?: string;
  showValue?: boolean;
  /** Override automatic score band color. */
  tone?: VariantProps<typeof ringToneClass>["tone"];
};

export function HealthScoreRing({
  className,
  value,
  max = 100,
  size = "md",
  label,
  showValue = true,
  tone,
  ...props
}: HealthScoreRingProps) {
  const dims = sizeMap[size];
  const clamped = Math.min(Math.max(value, 0), max);
  const radius = (dims.box - dims.stroke) / 2;
  const circumference = 2 * Math.PI * radius;
  const progress = max === 0 ? 0 : clamped / max;
  const offset = circumference * (1 - progress);
  const resolvedTone = tone ?? scoreTone(clamped, max);
  const ariaLabel = label ?? `Health score ${Math.round(clamped)} of ${max}`;

  return (
    <div
      role="img"
      aria-label={ariaLabel}
      className={cn("relative inline-flex items-center justify-center", className)}
      style={{ width: dims.box, height: dims.box }}
      {...props}
    >
      <svg
        width={dims.box}
        height={dims.box}
        viewBox={`0 0 ${dims.box} ${dims.box}`}
        className="-rotate-90"
        aria-hidden
      >
        <circle
          cx={dims.box / 2}
          cy={dims.box / 2}
          r={radius}
          fill="none"
          className="stroke-border"
          strokeWidth={dims.stroke}
        />
        <circle
          cx={dims.box / 2}
          cy={dims.box / 2}
          r={radius}
          fill="none"
          className={cn(ringToneClass({ tone: resolvedTone }), "transition-[stroke-dashoffset]")}
          style={{
            strokeWidth: dims.stroke,
            strokeLinecap: "round",
            strokeDasharray: circumference,
            strokeDashoffset: offset,
            transitionDuration: "var(--motion-score)",
          }}
          pathLength={circumference}
        />
      </svg>
      {showValue ? (
        <div className="absolute inset-0 flex flex-col items-center justify-center">
          <span className={cn("font-semibold tabular-nums text-foreground", dims.valueClass)}>
            {Math.round(clamped)}
          </span>
          <span className="text-[10px] text-foreground-muted">/{max}</span>
        </div>
      ) : null}
    </div>
  );
}

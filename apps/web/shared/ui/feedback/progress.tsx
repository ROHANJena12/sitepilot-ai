"use client";

import * as React from "react";
import { cva, type VariantProps } from "class-variance-authority";

import { cn } from "@/shared/lib/utils";

const progressVariants = cva("relative w-full overflow-hidden rounded-pill bg-surface-hover", {
  variants: {
    size: {
      sm: "h-1.5",
      md: "h-2",
      lg: "h-2.5",
    },
  },
  defaultVariants: {
    size: "md",
  },
});

export type ProgressProps = React.HTMLAttributes<HTMLDivElement> &
  VariantProps<typeof progressVariants> & {
    value: number;
    max?: number;
    label?: string;
  };

/**
 * Why new: DESIGN_SYSTEM ProgressBar was not in the prior DS foundation set.
 * Required for the audit analyzing experience (UI_SCREEN_SPEC Screen 3).
 */
export function Progress({
  className,
  value,
  max = 100,
  size,
  label = "Progress",
  ...props
}: ProgressProps) {
  const clamped = Math.min(Math.max(value, 0), max);
  const percent = max === 0 ? 0 : (clamped / max) * 100;

  return (
    <div
      role="progressbar"
      aria-label={label}
      aria-valuemin={0}
      aria-valuemax={max}
      aria-valuenow={Math.round(clamped)}
      className={cn(progressVariants({ size }), className)}
      {...props}
    >
      <div
        className="h-full rounded-pill bg-accent transition-[width] duration-base ease-out motion-reduce:transition-none"
        style={{ width: `${percent}%` }}
      />
    </div>
  );
}

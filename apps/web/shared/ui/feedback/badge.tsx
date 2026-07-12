import * as React from "react";
import { cva, type VariantProps } from "class-variance-authority";

import { cn } from "@/shared/lib/utils";

const badgeVariants = cva(
  "inline-flex items-center rounded-sm border px-2 py-0.5 text-xs font-medium transition-colors duration-fast",
  {
    variants: {
      variant: {
        neutral: "border-border bg-surface text-foreground-muted",
        success: "border-transparent bg-success/15 text-success",
        warning: "border-transparent bg-warning/15 text-warning",
        danger: "border-transparent bg-danger/15 text-danger",
        info: "border-transparent bg-info/15 text-info",
        accent: "border-transparent bg-accent-muted text-accent",
        critical: "border-transparent bg-priority-critical/15 text-priority-critical",
        high: "border-transparent bg-priority-high/15 text-priority-high",
        medium: "border-transparent bg-priority-medium/15 text-priority-medium",
        low: "border-transparent bg-priority-low/15 text-priority-low",
      },
      size: {
        sm: "px-1.5 py-0 text-[10px]",
        md: "px-2 py-0.5 text-xs",
      },
    },
    defaultVariants: {
      variant: "neutral",
      size: "md",
    },
  },
);

export type BadgeProps = React.HTMLAttributes<HTMLDivElement> &
  VariantProps<typeof badgeVariants>;

export function Badge({ className, variant, size, ...props }: BadgeProps) {
  return <div className={cn(badgeVariants({ variant, size }), className)} {...props} />;
}

export { badgeVariants };

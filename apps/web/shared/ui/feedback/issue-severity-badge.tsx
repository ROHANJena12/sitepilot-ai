import * as React from "react";
import { cva } from "class-variance-authority";

import { cn } from "@/shared/lib/utils";
import { Badge } from "@/shared/ui/feedback/badge";

const severityConfig = {
  critical: { label: "Critical", badge: "critical" as const },
  high: { label: "High", badge: "high" as const },
  medium: { label: "Medium", badge: "medium" as const },
  low: { label: "Low", badge: "low" as const },
};

export type IssueSeverity = keyof typeof severityConfig;

const severityDot = cva("mr-1.5 inline-block h-1.5 w-1.5 rounded-pill", {
  variants: {
    severity: {
      critical: "bg-priority-critical",
      high: "bg-priority-high",
      medium: "bg-priority-medium",
      low: "bg-priority-low",
    },
  },
});

export type IssueSeverityBadgeProps = Omit<
  React.ComponentProps<typeof Badge>,
  "variant" | "children"
> & {
  severity: IssueSeverity;
  /** Override default severity label text. */
  label?: string;
  showDot?: boolean;
};

export function IssueSeverityBadge({
  className,
  severity,
  label,
  showDot = true,
  size = "md",
  ...props
}: IssueSeverityBadgeProps) {
  const config = severityConfig[severity];

  return (
    <Badge
      variant={config.badge}
      size={size}
      className={cn("capitalize", className)}
      {...props}
    >
      {showDot ? (
        <span className={severityDot({ severity })} aria-hidden />
      ) : null}
      {label ?? config.label}
    </Badge>
  );
}

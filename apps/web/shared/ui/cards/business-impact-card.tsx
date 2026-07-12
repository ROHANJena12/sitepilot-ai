import * as React from "react";

import { cn } from "@/shared/lib/utils";
import { Card, CardContent, CardHeader, CardTitle } from "@/shared/ui/cards/card";
import { Text } from "@/shared/ui/typography/text";

export type BusinessImpactCardProps = React.HTMLAttributes<HTMLDivElement> & {
  domain: string;
  statement: string;
  signal?: string;
  icon?: React.ReactNode;
};

/**
 * Why new: DESIGN_SYSTEM §11.11 BusinessImpactCard was missing.
 * Required for Business Impact section on the report dashboard.
 */
export function BusinessImpactCard({
  className,
  domain,
  statement,
  signal,
  icon,
  ...props
}: BusinessImpactCardProps) {
  return (
    <Card
      className={cn(
        "h-full border-border/80 bg-surface/80 transition-colors duration-fast hover:bg-surface-hover",
        className,
      )}
      {...props}
    >
      <CardHeader className="pb-2">
        <div className="mb-3 flex items-center gap-3">
          {icon ? (
            <span className="inline-flex h-9 w-9 items-center justify-center rounded-md bg-accent-muted text-accent">
              {icon}
            </span>
          ) : null}
          <CardTitle className="text-sm font-medium text-foreground-muted">{domain}</CardTitle>
        </div>
        {signal ? (
          <p className="text-lg font-semibold tracking-tight text-foreground">{signal}</p>
        ) : null}
      </CardHeader>
      <CardContent className="pt-0">
        <Text variant="muted" className="text-sm leading-relaxed">
          {statement}
        </Text>
      </CardContent>
    </Card>
  );
}

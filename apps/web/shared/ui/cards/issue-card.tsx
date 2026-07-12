import * as React from "react";

import { cn } from "@/shared/lib/utils";
import { Card, CardContent, CardHeader, CardTitle } from "@/shared/ui/cards/card";
import { Badge } from "@/shared/ui/feedback/badge";
import {
  IssueSeverityBadge,
  type IssueSeverity,
} from "@/shared/ui/feedback/issue-severity-badge";
import { Text } from "@/shared/ui/typography/text";

export type IssueCardProps = React.HTMLAttributes<HTMLDivElement> & {
  title: string;
  severity: IssueSeverity;
  category: string;
  description: string;
  businessImpact: string;
  effort: string;
  confidence: number;
  status: string;
  /** Optional footer region (e.g. AI explain) — rendered inside the card below a divider. */
  children?: React.ReactNode;
};

/**
 * Finding card with optional collapsible footer section (AI explanation).
 */
export function IssueCard({
  className,
  title,
  severity,
  category,
  description,
  businessImpact,
  effort,
  confidence,
  status,
  children,
  ...props
}: IssueCardProps) {
  return (
    <Card
      className={cn(
        "overflow-hidden transition-colors duration-fast hover:bg-surface-hover focus-within:ring-2 focus-within:ring-accent",
        className,
      )}
      {...props}
    >
      <CardHeader className="gap-3 space-y-0 pb-3">
        <div className="flex flex-wrap items-center gap-2">
          <IssueSeverityBadge severity={severity} />
          <Badge variant="neutral">{category}</Badge>
          <Badge variant="info" size="sm">
            {confidence}% confidence
          </Badge>
          <Badge variant="accent" size="sm" className="sm:ml-auto">
            {status}
          </Badge>
        </div>
        <CardTitle className="text-base leading-snug">{title}</CardTitle>
      </CardHeader>
      <CardContent className={cn("space-y-3 pt-0", children ? "pb-4" : undefined)}>
        <Text variant="muted" className="text-sm leading-relaxed">
          {description}
        </Text>
        <dl className="grid gap-3 text-sm sm:grid-cols-2">
          <div>
            <dt className="text-xs font-medium text-foreground-subtle">Business impact</dt>
            <dd className="mt-1 text-foreground-muted">{businessImpact}</dd>
          </div>
          <div>
            <dt className="text-xs font-medium text-foreground-subtle">Estimated effort</dt>
            <dd className="mt-1 text-foreground-muted">{effort}</dd>
          </div>
        </dl>
      </CardContent>
      {children ? (
        <div className="border-t border-border bg-bg-subtle/40 px-4 py-3 md:px-6 md:py-4">
          {children}
        </div>
      ) : null}
    </Card>
  );
}

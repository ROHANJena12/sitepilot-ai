import * as React from "react";

import { cn } from "@/shared/lib/utils";
import { Card, CardContent, CardHeader, CardTitle } from "@/shared/ui/cards/card";
import { Badge } from "@/shared/ui/feedback/badge";
import { Text } from "@/shared/ui/typography/text";

export type RecommendationCardProps = React.HTMLAttributes<HTMLDivElement> & {
  title: string;
  priority: string;
  difficulty: string;
  estimatedImprovement: string;
  expectedImpact: string;
  confidence: number;
  /** Optional footer (e.g. AI explain) pinned to the bottom of the card. */
  children?: React.ReactNode;
};

/**
 * Recommendation / Quick Win card — vertical flex so the AI footer
 * aligns across a grid row regardless of content length.
 */
export function RecommendationCard({
  className,
  title,
  priority,
  difficulty,
  estimatedImprovement,
  expectedImpact,
  confidence,
  children,
  ...props
}: RecommendationCardProps) {
  return (
    <Card
      className={cn(
        "flex h-full flex-col overflow-hidden transition-colors duration-fast hover:bg-surface-hover",
        className,
      )}
      {...props}
    >
      <CardHeader className="shrink-0 gap-3 space-y-0 pb-3">
        <div className="flex flex-wrap items-center gap-2">
          <Badge variant="accent">{priority}</Badge>
          <Badge variant="neutral">{difficulty}</Badge>
          <Badge variant="info" size="sm">
            {confidence}% confidence
          </Badge>
        </div>
        <CardTitle className="text-base leading-snug">{title}</CardTitle>
      </CardHeader>
      <CardContent
        className={cn(
          "flex min-h-0 flex-1 flex-col space-y-3 pt-0",
          children ? "pb-4" : undefined,
        )}
      >
        <div className="space-y-3">
          <div>
            <p className="text-xs font-medium text-foreground-subtle">
              Estimated improvement
            </p>
            <Text variant="muted" className="mt-1 text-sm">
              {estimatedImprovement}
            </Text>
          </div>
          <div>
            <p className="text-xs font-medium text-foreground-subtle">Expected impact</p>
            <Text variant="muted" className="mt-1 text-sm">
              {expectedImpact}
            </Text>
          </div>
        </div>
        {/* Spacer pushes the AI footer to the bottom of equal-height cards */}
        {children ? <div className="min-h-0 flex-1" aria-hidden /> : null}
      </CardContent>
      {children ? (
        <div className="mt-auto shrink-0 border-t border-border bg-bg-subtle/40 px-4 py-3 md:px-6 md:py-4">
          {children}
        </div>
      ) : null}
    </Card>
  );
}

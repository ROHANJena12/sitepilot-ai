import * as React from "react";

import { cn } from "@/shared/lib/utils";
import { Card, CardContent, CardHeader } from "@/shared/ui/cards/card";
import { Text } from "@/shared/ui/typography/text";
import { HealthScoreRing } from "@/shared/ui/charts/health-score-ring";
import { Skeleton } from "@/shared/ui/feedback/skeleton";

export type ScoreCardProps = React.HTMLAttributes<HTMLDivElement> & {
  label: string;
  value: number;
  max?: number;
  description?: string;
  size?: React.ComponentProps<typeof HealthScoreRing>["size"];
  loading?: boolean;
};

export function ScoreCard({
  className,
  label,
  value,
  max = 100,
  description,
  size = "md",
  loading = false,
  ...props
}: ScoreCardProps) {
  return (
    <Card
      className={cn(
        "flex flex-col items-center text-center transition-colors duration-fast hover:bg-surface-hover",
        className,
      )}
      {...props}
    >
      <CardHeader className="pb-2">
        <Text variant="muted">{label}</Text>
      </CardHeader>
      <CardContent className="flex flex-col items-center gap-3 pt-0">
        {loading ? (
          <Skeleton className="h-28 w-28 rounded-pill" />
        ) : (
          <HealthScoreRing value={value} max={max} size={size} label={`${label}: ${value} of ${max}`} />
        )}
        {description ? (
          <Text variant="caption">{description}</Text>
        ) : null}
      </CardContent>
    </Card>
  );
}

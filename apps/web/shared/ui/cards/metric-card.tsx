import * as React from "react";
import { cva, type VariantProps } from "class-variance-authority";
import { TrendingDown, TrendingUp, Minus } from "lucide-react";

import { cn } from "@/shared/lib/utils";
import { Card, CardContent, CardHeader } from "@/shared/ui/cards/card";
import { Text } from "@/shared/ui/typography/text";
import { Skeleton } from "@/shared/ui/feedback/skeleton";

const deltaVariants = cva("inline-flex items-center gap-1 text-xs font-medium", {
  variants: {
    tone: {
      positive: "text-success",
      negative: "text-danger",
      neutral: "text-foreground-muted",
    },
  },
  defaultVariants: {
    tone: "neutral",
  },
});

export type MetricCardProps = React.HTMLAttributes<HTMLDivElement> & {
  label: string;
  value: React.ReactNode;
  delta?: {
    value: string;
    tone?: VariantProps<typeof deltaVariants>["tone"];
  };
  description?: string;
  loading?: boolean;
};

export function MetricCard({
  className,
  label,
  value,
  delta,
  description,
  loading = false,
  ...props
}: MetricCardProps) {
  return (
    <Card className={cn("transition-colors duration-fast hover:bg-surface-hover", className)} {...props}>
      <CardHeader className="pb-2">
        <Text variant="muted">{label}</Text>
      </CardHeader>
      <CardContent>
        {loading ? (
          <div className="space-y-2">
            <Skeleton className="h-8 w-24" />
            <Skeleton className="h-4 w-16" />
          </div>
        ) : (
          <>
            <div className="text-2xl font-semibold tracking-tight text-foreground md:text-3xl">
              {value}
            </div>
            {(delta || description) && (
              <div className="mt-2 flex flex-wrap items-center gap-2">
                {delta ? (
                  <span className={cn(deltaVariants({ tone: delta.tone }))}>
                    {delta.tone === "positive" ? (
                      <TrendingUp className="h-3.5 w-3.5" aria-hidden />
                    ) : delta.tone === "negative" ? (
                      <TrendingDown className="h-3.5 w-3.5" aria-hidden />
                    ) : (
                      <Minus className="h-3.5 w-3.5" aria-hidden />
                    )}
                    {delta.value}
                  </span>
                ) : null}
                {description ? (
                  <Text as="span" variant="caption">
                    {description}
                  </Text>
                ) : null}
              </div>
            )}
          </>
        )}
      </CardContent>
    </Card>
  );
}

/** Compact metric layout for dashboard stat strips. */
export type StatCardProps = MetricCardProps;

export function StatCard(props: StatCardProps) {
  return <MetricCard {...props} />;
}

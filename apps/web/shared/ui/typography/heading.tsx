import * as React from "react";
import { cva, type VariantProps } from "class-variance-authority";

import { cn } from "@/shared/lib/utils";

const headingVariants = cva("font-semibold text-foreground tracking-tight", {
  variants: {
    level: {
      display: "text-4xl md:text-5xl lg:text-[56px] leading-[1.05] tracking-[-0.02em]",
      h1: "text-3xl md:text-4xl leading-[1.15] tracking-[-0.02em]",
      h2: "text-2xl md:text-[32px] leading-[1.2] tracking-[-0.015em]",
      h3: "text-xl md:text-2xl leading-[1.25]",
      h4: "text-lg leading-[1.35]",
    },
  },
  defaultVariants: {
    level: "h2",
  },
});

type Level = NonNullable<VariantProps<typeof headingVariants>["level"]>;

const tagMap: Record<Level, keyof React.JSX.IntrinsicElements> = {
  display: "h1",
  h1: "h1",
  h2: "h2",
  h3: "h3",
  h4: "h4",
};

export type HeadingProps = React.HTMLAttributes<HTMLHeadingElement> &
  VariantProps<typeof headingVariants> & {
    as?: keyof React.JSX.IntrinsicElements;
  };

export function Heading({ className, level = "h2", as, ...props }: HeadingProps) {
  const Comp = (as ?? tagMap[level ?? "h2"]) as React.ElementType;
  return <Comp className={cn(headingVariants({ level }), className)} {...props} />;
}

import * as React from "react";
import { cva, type VariantProps } from "class-variance-authority";

import { cn } from "@/shared/lib/utils";

const textVariants = cva("text-foreground", {
  variants: {
    variant: {
      body: "text-base leading-[1.55]",
      "body-sm": "text-sm leading-[1.5]",
      caption: "text-xs leading-[1.4] tracking-[0.01em] text-foreground-muted",
      label: "text-[13px] font-medium leading-[1.3] tracking-[0.02em]",
      muted: "text-sm text-foreground-muted",
      code: "font-mono text-[13px] leading-[1.5]",
    },
  },
  defaultVariants: {
    variant: "body",
  },
});

export type TextProps = React.HTMLAttributes<HTMLElement> &
  VariantProps<typeof textVariants> & {
    as?: "p" | "span" | "div" | "label" | "code";
  };

export function Text({ className, variant, as, ...props }: TextProps) {
  const Comp = (as ?? (variant === "code" ? "code" : "p")) as React.ElementType;
  return <Comp className={cn(textVariants({ variant }), className)} {...props} />;
}

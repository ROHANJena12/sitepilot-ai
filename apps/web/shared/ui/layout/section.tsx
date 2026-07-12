import * as React from "react";
import { cva, type VariantProps } from "class-variance-authority";

import { cn } from "@/shared/lib/utils";

const sectionVariants = cva("w-full", {
  variants: {
    spacing: {
      sm: "py-8 md:py-10",
      md: "py-12 md:py-16",
      lg: "py-16 md:py-24",
      none: "py-0",
    },
  },
  defaultVariants: {
    spacing: "md",
  },
});

export type SectionProps = React.HTMLAttributes<HTMLElement> &
  VariantProps<typeof sectionVariants>;

export function Section({ className, spacing, ...props }: SectionProps) {
  return <section className={cn(sectionVariants({ spacing }), className)} {...props} />;
}

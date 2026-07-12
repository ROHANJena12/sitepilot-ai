"use client";

import * as React from "react";
import * as LabelPrimitive from "@radix-ui/react-label";
import { cva, type VariantProps } from "class-variance-authority";

import { cn } from "@/shared/lib/utils";

const labelVariants = cva(
  "font-medium leading-none text-foreground peer-disabled:cursor-not-allowed peer-disabled:opacity-[var(--opacity-disabled)]",
  {
    variants: {
      size: {
        sm: "text-xs",
        md: "text-[13px]",
      },
    },
    defaultVariants: {
      size: "md",
    },
  },
);

export type LabelProps = React.ComponentPropsWithoutRef<typeof LabelPrimitive.Root> &
  VariantProps<typeof labelVariants>;

export const Label = React.forwardRef<
  React.ElementRef<typeof LabelPrimitive.Root>,
  LabelProps
>(({ className, size, ...props }, ref) => (
  <LabelPrimitive.Root
    ref={ref}
    className={cn(labelVariants({ size }), className)}
    {...props}
  />
));
Label.displayName = LabelPrimitive.Root.displayName;

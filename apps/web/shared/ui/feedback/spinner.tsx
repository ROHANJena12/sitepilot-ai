import * as React from "react";
import { Loader2 } from "lucide-react";
import { cva, type VariantProps } from "class-variance-authority";

import { cn } from "@/shared/lib/utils";

const spinnerVariants = cva("animate-spin text-accent", {
  variants: {
    size: {
      sm: "h-4 w-4",
      md: "h-5 w-5",
      lg: "h-8 w-8",
    },
  },
  defaultVariants: {
    size: "md",
  },
});

export type SpinnerProps = React.SVGAttributes<SVGSVGElement> &
  VariantProps<typeof spinnerVariants> & {
    label?: string;
  };

export function Spinner({ className, size, label = "Loading", ...props }: SpinnerProps) {
  return (
    <Loader2
      role="status"
      aria-label={label}
      className={cn(spinnerVariants({ size }), className)}
      {...props}
    />
  );
}

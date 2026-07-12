import * as React from "react";
import { cva, type VariantProps } from "class-variance-authority";

import { cn } from "@/shared/lib/utils";

const inputVariants = cva(
  "flex w-full rounded-md border bg-surface text-foreground transition-colors duration-fast file:border-0 file:bg-transparent file:text-sm file:font-medium placeholder:text-foreground-subtle focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-accent focus-visible:ring-offset-2 focus-visible:ring-offset-bg disabled:cursor-not-allowed disabled:opacity-[var(--opacity-disabled)]",
  {
    variants: {
      variant: {
        default: "border-border",
        ghost: "border-transparent bg-transparent shadow-none",
      },
      size: {
        sm: "h-8 px-3 text-xs",
        md: "h-10 px-3 text-sm",
        lg: "h-11 px-4 text-base",
      },
      state: {
        default: "",
        error: "border-danger focus-visible:ring-danger",
        success: "border-success",
      },
    },
    defaultVariants: {
      variant: "default",
      size: "md",
      state: "default",
    },
  },
);

export type InputProps = Omit<React.InputHTMLAttributes<HTMLInputElement>, "size"> &
  VariantProps<typeof inputVariants> & {
    error?: boolean;
  };

export const Input = React.forwardRef<HTMLInputElement, InputProps>(
  ({ className, variant, size, state, error, type = "text", ...props }, ref) => {
    return (
      <input
        type={type}
        className={cn(
          inputVariants({
            variant,
            size,
            state: error ? "error" : state,
            className,
          }),
        )}
        ref={ref}
        aria-invalid={error || state === "error" ? true : undefined}
        {...props}
      />
    );
  },
);
Input.displayName = "Input";

export { inputVariants };

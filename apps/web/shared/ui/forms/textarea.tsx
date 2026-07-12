import * as React from "react";

import { cn } from "@/shared/lib/utils";

export type TextareaProps = React.TextareaHTMLAttributes<HTMLTextAreaElement> & {
  error?: boolean;
};

export const Textarea = React.forwardRef<HTMLTextAreaElement, TextareaProps>(
  ({ className, error, ...props }, ref) => {
    return (
      <textarea
        className={cn(
          "flex min-h-24 w-full rounded-md border border-border bg-surface px-3 py-2 text-sm text-foreground transition-colors duration-fast placeholder:text-foreground-subtle focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-accent focus-visible:ring-offset-2 focus-visible:ring-offset-bg disabled:cursor-not-allowed disabled:opacity-[var(--opacity-disabled)]",
          error && "border-danger focus-visible:ring-danger",
          className,
        )}
        ref={ref}
        aria-invalid={error ? true : undefined}
        {...props}
      />
    );
  },
);
Textarea.displayName = "Textarea";

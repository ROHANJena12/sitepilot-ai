import * as React from "react";
import { ChevronRight, MoreHorizontal } from "lucide-react";
import { Slot } from "@radix-ui/react-slot";

import { cn } from "@/shared/lib/utils";

export function Breadcrumb({ className, ...props }: React.ComponentPropsWithoutRef<"nav">) {
  return <nav aria-label="Breadcrumb" className={cn("w-full", className)} {...props} />;
}

export function BreadcrumbList({ className, ...props }: React.ComponentPropsWithoutRef<"ol">) {
  return (
    <ol
      className={cn(
        "flex flex-wrap items-center gap-1.5 break-words text-sm text-foreground-muted sm:gap-2",
        className,
      )}
      {...props}
    />
  );
}

export function BreadcrumbItem({ className, ...props }: React.ComponentPropsWithoutRef<"li">) {
  return <li className={cn("inline-flex items-center gap-1.5", className)} {...props} />;
}

export type BreadcrumbLinkProps = React.ComponentPropsWithoutRef<"a"> & {
  asChild?: boolean;
};

export function BreadcrumbLink({ asChild, className, ...props }: BreadcrumbLinkProps) {
  const Comp = asChild ? Slot : "a";
  return (
    <Comp
      className={cn("transition-colors hover:text-foreground focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-accent", className)}
      {...props}
    />
  );
}

export function BreadcrumbPage({ className, ...props }: React.ComponentPropsWithoutRef<"span">) {
  return (
    <span
      role="link"
      aria-disabled="true"
      aria-current="page"
      className={cn("font-medium text-foreground", className)}
      {...props}
    />
  );
}

export function BreadcrumbSeparator({
  children,
  className,
  ...props
}: React.ComponentPropsWithoutRef<"li">) {
  return (
    <li role="presentation" aria-hidden="true" className={cn("[&>svg]:h-3.5 [&>svg]:w-3.5", className)} {...props}>
      {children ?? <ChevronRight />}
    </li>
  );
}

export function BreadcrumbEllipsis({ className, ...props }: React.ComponentPropsWithoutRef<"span">) {
  return (
    <span
      role="presentation"
      aria-hidden="true"
      className={cn("flex h-9 w-9 items-center justify-center", className)}
      {...props}
    >
      <MoreHorizontal className="h-4 w-4" />
      <span className="sr-only">More</span>
    </span>
  );
}

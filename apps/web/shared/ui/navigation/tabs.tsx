"use client";

import * as React from "react";
import * as TabsPrimitive from "@radix-ui/react-tabs";
import { cva, type VariantProps } from "class-variance-authority";

import { cn } from "@/shared/lib/utils";

export const Tabs = TabsPrimitive.Root;

const tabsListVariants = cva("inline-flex items-center justify-center text-foreground-muted", {
  variants: {
    variant: {
      line: "h-10 w-full justify-start gap-6 border-b border-border bg-transparent p-0",
      enclosed: "h-10 rounded-md bg-bg-subtle p-1",
    },
  },
  defaultVariants: {
    variant: "line",
  },
});

export type TabsListProps = React.ComponentPropsWithoutRef<typeof TabsPrimitive.List> &
  VariantProps<typeof tabsListVariants>;

export const TabsList = React.forwardRef<
  React.ElementRef<typeof TabsPrimitive.List>,
  TabsListProps
>(({ className, variant, ...props }, ref) => (
  <TabsPrimitive.List
    ref={ref}
    className={cn(tabsListVariants({ variant }), className)}
    {...props}
  />
));
TabsList.displayName = TabsPrimitive.List.displayName;

const tabsTriggerVariants = cva(
  "inline-flex items-center justify-center whitespace-nowrap text-sm font-medium transition-all focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-accent disabled:pointer-events-none disabled:opacity-[var(--opacity-disabled)]",
  {
    variants: {
      variant: {
        line: "rounded-none border-b-2 border-transparent px-1 pb-3 pt-2 data-[state=active]:border-accent data-[state=active]:text-foreground",
        enclosed:
          "rounded-sm px-3 py-1.5 data-[state=active]:bg-surface data-[state=active]:text-foreground data-[state=active]:shadow-sm",
      },
    },
    defaultVariants: {
      variant: "line",
    },
  },
);

export type TabsTriggerProps = React.ComponentPropsWithoutRef<typeof TabsPrimitive.Trigger> &
  VariantProps<typeof tabsTriggerVariants>;

export const TabsTrigger = React.forwardRef<
  React.ElementRef<typeof TabsPrimitive.Trigger>,
  TabsTriggerProps
>(({ className, variant, ...props }, ref) => (
  <TabsPrimitive.Trigger
    ref={ref}
    className={cn(tabsTriggerVariants({ variant }), className)}
    {...props}
  />
));
TabsTrigger.displayName = TabsPrimitive.Trigger.displayName;

export const TabsContent = React.forwardRef<
  React.ElementRef<typeof TabsPrimitive.Content>,
  React.ComponentPropsWithoutRef<typeof TabsPrimitive.Content>
>(({ className, ...props }, ref) => (
  <TabsPrimitive.Content
    ref={ref}
    className={cn("mt-4 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-accent", className)}
    {...props}
  />
));
TabsContent.displayName = TabsPrimitive.Content.displayName;

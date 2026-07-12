import Link from "next/link";

import { cn } from "@/shared/lib/utils";
import { ROUTES } from "@/shared/constants/routes";
import { siteConfig } from "@/shared/config/site";

export type BrandLogoProps = {
  className?: string;
  /** Show wordmark text next to the mark. */
  showWordmark?: boolean;
  /** Compact size for dense chrome. */
  size?: "sm" | "md";
};

/**
 * Why new: no brand mark existed in shared/ui. Nav and footer both need a
 * consistent SitePilot wordmark that links home (DESIGN_SYSTEM §3.7).
 */
export function BrandLogo({
  className,
  showWordmark = true,
  size = "md",
}: BrandLogoProps) {
  const markSize = size === "sm" ? "h-6 w-6" : "h-7 w-7";
  const textSize = size === "sm" ? "text-sm" : "text-base";

  return (
    <Link
      href={ROUTES.home}
      className={cn(
        "inline-flex items-center gap-2.5 rounded-md text-foreground transition-opacity duration-fast hover:opacity-90 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-accent focus-visible:ring-offset-2 focus-visible:ring-offset-bg",
        className,
      )}
      aria-label={`${siteConfig.name} home`}
    >
      <span
        className={cn(
          "relative inline-flex shrink-0 items-center justify-center rounded-md bg-accent-muted",
          markSize,
        )}
        aria-hidden
      >
        <span className="absolute inset-[3px] rounded-[calc(var(--radius-sm)-1px)] border border-accent/40" />
        <span className="h-1.5 w-1.5 rounded-pill bg-accent" />
      </span>
      {showWordmark ? (
        <span className={cn("font-semibold tracking-tight", textSize)}>
          {siteConfig.name}
        </span>
      ) : null}
    </Link>
  );
}

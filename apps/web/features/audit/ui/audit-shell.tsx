import * as React from "react";
import Link from "next/link";

import { BrandLogo } from "@/shared/ui/brand";
import { ThemeToggle } from "@/shared/ui/theme-toggle";
import { Container } from "@/shared/ui/layout";
import { ROUTES } from "@/shared/constants/routes";

type AuditShellProps = {
  children: React.ReactNode;
  /** Optional right-side status text */
  status?: string;
};

/**
 * Minimal chrome for audit/report flow pages — not full marketing nav.
 */
export function AuditShell({ children, status }: AuditShellProps) {
  return (
    <div className="flex min-h-dvh flex-col bg-bg">
      <header className="sticky top-0 z-30 border-b border-border/80 bg-bg/80 backdrop-blur-md">
        <Container className="flex h-14 items-center justify-between gap-4 md:h-16">
          <BrandLogo size="sm" />
          <div className="flex items-center gap-3">
            {status ? (
              <p className="hidden text-xs text-foreground-muted sm:block">{status}</p>
            ) : null}
            <Link
              href={ROUTES.home}
              className="hidden text-sm text-foreground-muted transition-colors hover:text-foreground focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-accent sm:inline"
            >
              Home
            </Link>
            <ThemeToggle />
          </div>
        </Container>
      </header>
      <div className="flex-1">{children}</div>
    </div>
  );
}

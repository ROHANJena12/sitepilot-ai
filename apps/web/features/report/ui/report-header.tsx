"use client";

import Link from "next/link";
import { RotateCcw, ExternalLink } from "lucide-react";

import { ROUTES } from "@/shared/constants/routes";
import { BrandLogo } from "@/shared/ui/brand";
import { Button } from "@/shared/ui/buttons";
import { Badge } from "@/shared/ui/feedback";
import { ThemeToggle } from "@/shared/ui/theme-toggle";
import { Container } from "@/shared/ui/layout";
import { Text } from "@/shared/ui/typography";
import type { ReportDashboardView } from "../model/map-api-report";
import { ReportExportMenu } from "./report-export-menu";
import { ReportShareMenu } from "./report-share-menu";

type ReportHeaderProps = {
  auditId: string;
  report: Pick<ReportDashboardView, "websiteUrl" | "host" | "status" | "auditDate">;
  readonly?: boolean;
};

export function ReportHeader({ auditId, report, readonly = false }: ReportHeaderProps) {
  return (
    <header className="sticky top-0 z-40 border-b border-border/80 bg-bg/85 backdrop-blur-md">
      <Container className="flex flex-col gap-3 py-3 sm:flex-row sm:items-center sm:justify-between md:h-16 md:py-0">
        <div className="flex min-w-0 items-center gap-3">
          <BrandLogo size="sm" showWordmark={false} className="shrink-0" />
          <div className="min-w-0">
            <div className="flex flex-wrap items-center gap-2">
              <a
                href={report.websiteUrl}
                target="_blank"
                rel="noopener noreferrer"
                className="inline-flex max-w-full items-center gap-1.5 truncate rounded-sm text-sm font-semibold text-foreground transition-colors duration-fast hover:text-accent focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-accent focus-visible:ring-offset-2 focus-visible:ring-offset-bg"
              >
                <span className="truncate">{report.host}</span>
                <ExternalLink className="h-3.5 w-3.5 shrink-0 opacity-60" aria-hidden />
                <span className="sr-only">(opens in new tab)</span>
              </a>
              <Badge variant="success" size="sm">
                {report.status}
              </Badge>
              {readonly ? (
                <Badge variant="neutral" size="sm">
                  Shared · read-only
                </Badge>
              ) : null}
            </div>
            <Text as="p" variant="caption" className="mt-0.5 text-foreground-subtle">
              Audit · {report.auditDate}
            </Text>
          </div>
        </div>

        <div className="flex flex-wrap items-center gap-2">
          {!readonly ? (
            <>
              <ReportExportMenu auditId={auditId} />
              <ReportShareMenu auditId={auditId} />
              <Button asChild size="sm" variant="primary" className="flex-1 sm:flex-none">
                <Link href={ROUTES.audit}>
                  <RotateCcw className="mr-1.5 h-3.5 w-3.5" aria-hidden />
                  New audit
                </Link>
              </Button>
            </>
          ) : null}
          <ThemeToggle />
        </div>
      </Container>
    </header>
  );
}

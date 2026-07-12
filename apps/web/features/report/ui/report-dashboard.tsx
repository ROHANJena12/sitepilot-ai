"use client";

"use client";

import * as React from "react";
import Link from "next/link";

import { Container } from "@/shared/ui/layout";
import { Skeleton, Separator } from "@/shared/ui/feedback";
import { Button } from "@/shared/ui/buttons";
import { Heading, Text } from "@/shared/ui/typography";
import { isApiError } from "@/shared/types/api";
import { ROUTES } from "@/shared/constants/routes";
import { useAuditReport, useSharedReport } from "@/shared/hooks/useReport";
import {
  useGenerateBusinessSummary,
  useGenerateExecutiveSummary,
  useGenerateFinding,
  useGenerateQuickWin,
  useGenerateRecommendation,
  useRegenerateBusinessSummary,
  useRegenerateExecutiveSummary,
  useRegenerateFinding,
} from "@/shared/hooks/useAi";
import { aiService } from "@/shared/services/ai.service";

import { mapAuditReportToDashboard, type ReportDashboardView } from "../model/map-api-report";
import { ReportHeader } from "./report-header";
import { ExecutiveSummary } from "./executive-summary";
import { OverallHealth } from "./overall-health";
import { ScoreCardsGrid } from "./score-cards-grid";
import { CriticalIssues } from "./critical-issues";
import { AiRecommendations } from "./ai-recommendations";
import { BusinessImpactSection } from "./business-impact-section";
import { EstimatedRoi } from "./estimated-roi";
import { ReportChartsSection } from "./report-charts-section";
import { ActionPanel } from "./action-panel";
import { AiExplainPanel } from "./ai-explain-panel";

function ReportSkeleton() {
  return (
    <Container
      className="max-w-6xl space-y-8 py-6 md:space-y-10 md:py-8"
      aria-busy="true"
      aria-label="Loading report"
    >
      <Skeleton className="h-36 w-full rounded-lg md:h-40" />
      <Skeleton className="h-44 w-full rounded-lg md:h-52" />
      <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
        {Array.from({ length: 6 }).map((_, i) => (
          <Skeleton key={i} className="h-40 rounded-lg md:h-44" />
        ))}
      </div>
    </Container>
  );
}

type ReportDashboardProps = {
  /** Live report mode — loads GET /audits/{id}/report */
  auditId?: string;
  /** Shared read-only mode — loads GET /share/{token} */
  shareToken?: string;
  /** Hide AI / export / share / regenerate controls */
  readonly?: boolean;
};

/**
 * Live or shared report dashboard.
 *
 * Shared links set ``readonly`` (and usually ``shareToken``) so viewers cannot
 * regenerate AI, export, or share again from this surface.
 */
export function ReportDashboard({
  auditId,
  shareToken,
  readonly = false,
}: ReportDashboardProps) {
  const isShared = Boolean(shareToken);
  const readOnly = readonly || isShared;

  const liveQuery = useAuditReport(isShared ? null : auditId);
  const sharedQuery = useSharedReport(isShared ? shareToken : null);
  const reportQuery = isShared ? sharedQuery : liveQuery;

  const genExec = useGenerateExecutiveSummary();
  const regenExec = useRegenerateExecutiveSummary();
  const genBiz = useGenerateBusinessSummary();
  const regenBiz = useRegenerateBusinessSummary();
  const genFinding = useGenerateFinding();
  const regenFinding = useRegenerateFinding();
  const genRec = useGenerateRecommendation();
  const genQw = useGenerateQuickWin();

  const view: ReportDashboardView | null = React.useMemo(() => {
    if (!reportQuery.data) return null;
    return mapAuditReportToDashboard(reportQuery.data);
  }, [reportQuery.data]);

  const resolvedAuditId = auditId || reportQuery.data?.audit_id || "";

  if (reportQuery.isLoading) {
    return (
      <div className="min-h-dvh bg-bg">
        <ReportSkeleton />
      </div>
    );
  }

  if (reportQuery.isError || !view) {
    const status = (reportQuery.error as { status?: number } | undefined)?.status;
    const message = isApiError(reportQuery.error)
      ? reportQuery.error.message
      : status === 410
        ? "This share link has expired."
        : "Could not load report";
    return (
      <div className="flex min-h-dvh flex-col items-center justify-center gap-4 bg-bg px-4">
        <Heading level="h1" className="text-xl">
          {status === 410 ? "Share link expired" : "Report unavailable"}
        </Heading>
        <Text variant="muted" className="max-w-md text-center">
          {message}
        </Text>
        <div className="flex flex-wrap items-center justify-center gap-2">
          {!readOnly ? (
            <Button type="button" variant="secondary" onClick={() => void reportQuery.refetch()}>
              Retry
            </Button>
          ) : null}
          <Button asChild variant="secondary">
            <Link href={ROUTES.home}>Go home</Link>
          </Button>
          <Button asChild>
            <Link href={ROUTES.audit}>New audit</Link>
          </Button>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-dvh bg-bg">
      <a href="#report-main" className="skip-link">
        Skip to report
      </a>
      <ReportHeader auditId={resolvedAuditId} report={view} readonly={readOnly} />
      <main id="report-main" className="pb-14 pt-5 md:pb-16 md:pt-8">
        <Container className="max-w-6xl space-y-10 md:space-y-14">
          <section className="space-y-3">
            <ExecutiveSummary
              bullets={view.summaryBullets}
              subtitle={
                readOnly
                  ? "Read-only shared report — AI actions and exports are disabled."
                  : "Deterministic report summary from the audit pipeline."
              }
            />
            {!readOnly ? (
              <>
                <AiExplainPanel
                  title="AI executive summary"
                  onGenerate={(onProgress) =>
                    genExec.mutateAsync({ id: resolvedAuditId, onProgress })
                  }
                  onRegenerate={() => regenExec.mutateAsync(resolvedAuditId)}
                />
                <AiExplainPanel
                  title="AI business summary"
                  onGenerate={(onProgress) =>
                    genBiz.mutateAsync({ id: resolvedAuditId, onProgress })
                  }
                  onRegenerate={() => regenBiz.mutateAsync(resolvedAuditId)}
                />
              </>
            ) : null}
          </section>

          <OverallHealth score={view.overallHealth} host={view.host} />
          <ScoreCardsGrid scores={view.scores} />
          <Separator />

          <CriticalIssues
            issues={view.issues}
            renderAi={
              readOnly
                ? undefined
                : (issue) =>
                    issue.resourceId ? (
                      <AiExplainPanel
                        variant="embedded"
                        title="Explain this finding"
                        onGenerate={(onProgress) =>
                          genFinding.mutateAsync({ id: issue.resourceId!, onProgress })
                        }
                        onRegenerate={() => regenFinding.mutateAsync(issue.resourceId!)}
                      />
                    ) : null
            }
          />

          <AiRecommendations
            recommendations={view.recommendations}
            heading="Recommendations"
            subtitle={
              readOnly
                ? "Rule-based actions from the recommendation engine."
                : "Rule-based actions from the recommendation engine. Generate AI explanations per item."
            }
            renderAi={
              readOnly
                ? undefined
                : (rec) =>
                    rec.resourceId ? (
                      <AiExplainPanel
                        variant="embedded"
                        title="Explain recommendation"
                        onGenerate={(onProgress) =>
                          genRec.mutateAsync({ id: rec.resourceId!, onProgress })
                        }
                        onRegenerate={() =>
                          aiService.regenerateRecommendation(rec.resourceId!)
                        }
                      />
                    ) : null
            }
          />

          {view.quickWins.length > 0 ? (
            <AiRecommendations
              recommendations={view.quickWins}
              heading="Quick wins"
              subtitle="High-impact, lower-effort recommendations."
              renderAi={
                readOnly
                  ? undefined
                  : (rec) =>
                      rec.resourceId ? (
                        <AiExplainPanel
                          variant="embedded"
                          title="Quick-win explanation"
                          onGenerate={(onProgress) =>
                            genQw.mutateAsync({ id: rec.resourceId!, onProgress })
                          }
                          onRegenerate={() => aiService.regenerateQuickWin(rec.resourceId!)}
                        />
                      ) : null
              }
            />
          ) : null}

          <BusinessImpactSection items={view.businessImpact} />
          <EstimatedRoi roi={view.roi} />
          <ReportChartsSection charts={view.charts} />
          {!readOnly && resolvedAuditId ? (
            <ActionPanel auditId={resolvedAuditId} readonly={readOnly} />
          ) : null}
        </Container>
      </main>
    </div>
  );
}

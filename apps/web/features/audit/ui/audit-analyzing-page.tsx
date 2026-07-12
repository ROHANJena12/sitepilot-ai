"use client";

import * as React from "react";
import { useRouter, useSearchParams } from "next/navigation";
import { motion, useReducedMotion } from "framer-motion";

import { ROUTES, reportPath } from "@/shared/constants/routes";
import { ANIMATIONS, EASE_OUT } from "@/shared/constants/animations";
import { useAuditStatus, useCreateAudit } from "@/shared/hooks/useAudit";
import { toUserFacingError } from "@/shared/lib/user-facing-error";
import { isApiError } from "@/shared/types/api";
import {
  isSuccessfulAuditStatus,
  isTerminalAuditStatus,
} from "@/shared/types/audit";
import { Badge, Progress, Spinner } from "@/shared/ui/feedback";
import { Button } from "@/shared/ui/buttons";
import { Card, CardContent, CardHeader, CardTitle } from "@/shared/ui/cards";
import { Container, Section } from "@/shared/ui/layout";
import { Heading, Text } from "@/shared/ui/typography";

import {
  clearAuditInFlight,
  clearPendingAuditUrl,
  clearPendingWebsiteId,
  getCompletedAuditForWebsite,
  getPendingAuditUrl,
  getPendingWebsiteId,
  isAuditInFlight,
  markAuditInFlight,
  setCompletedAuditForWebsite,
} from "../lib/audit-session";
import {
  PIPELINE_ENGINES,
  engineIndexFor,
} from "../model/pipeline-engines";
import { AuditShell } from "./audit-shell";
import { EngineTimeline } from "./engine-timeline";

function displayHost(url: string) {
  try {
    return new URL(url).hostname;
  } catch {
    return url;
  }
}

function engineLabel(key: string | null | undefined): string {
  if (!key) return "Preparing…";
  const idx = engineIndexFor(key);
  if (idx >= 0) return PIPELINE_ENGINES[idx]!.label;
  return key;
}

export function AuditAnalyzingPage() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const reduceMotion = useReducedMotion();
  const createAudit = useCreateAudit();

  const [websiteUrl, setWebsiteUrl] = React.useState<string | null>(null);
  const [websiteId, setWebsiteId] = React.useState<string | null>(null);
  const [auditId, setAuditId] = React.useState<string | null>(null);
  const [error, setError] = React.useState<string | null>(null);
  const [failed, setFailed] = React.useState(false);
  const [blockedDuplicate, setBlockedDuplicate] = React.useState(false);
  const started = React.useRef(false);

  const auditStatus = useAuditStatus(auditId);

  React.useEffect(() => {
    const qAuditId = searchParams.get("auditId");
    const qId = searchParams.get("websiteId");
    const qUrl = searchParams.get("url");
    const sid = qId || getPendingWebsiteId();
    const surl = qUrl || getPendingAuditUrl();

    // Audit already created (landing hero) — poll only, do not POST again.
    if (qAuditId && sid && surl) {
      const completed = getCompletedAuditForWebsite(sid);
      if (completed) {
        router.replace(reportPath(completed));
        return;
      }
      clearPendingAuditUrl();
      clearPendingWebsiteId();
      clearAuditInFlight(sid);
      setWebsiteId(sid);
      setWebsiteUrl(surl);
      setAuditId(qAuditId);
      started.current = true;
      return;
    }

    if (!sid || !surl) {
      router.replace(ROUTES.audit);
      return;
    }

    const completed = getCompletedAuditForWebsite(sid);
    if (completed) {
      router.replace(reportPath(completed));
      return;
    }

    setWebsiteId(sid);
    setWebsiteUrl(surl);
  }, [router, searchParams]);

  React.useEffect(() => {
    if (!websiteId || started.current) return;
    started.current = true;

    if (isAuditInFlight(websiteId)) {
      setBlockedDuplicate(true);
      setFailed(true);
      setError(
        "An audit for this site may already be running. Wait a moment, then retry or start with another URL.",
      );
      return;
    }

    void (async () => {
      markAuditInFlight(websiteId);
      try {
        const result = await createAudit.mutateAsync(websiteId);
        clearPendingAuditUrl();
        clearPendingWebsiteId();
        setAuditId(result.audit_id);

        // If the API still returns a terminal status (legacy sync), finish immediately.
        if (isTerminalAuditStatus(result.status)) {
          clearAuditInFlight(websiteId);
          if (isSuccessfulAuditStatus(result.status)) {
            setCompletedAuditForWebsite(websiteId, result.audit_id);
            router.replace(reportPath(result.audit_id));
            return;
          }
          setFailed(true);
          setError(
            toUserFacingError(
              result.message || `Audit ${result.status}`,
              "The audit did not finish successfully. Try again or use another URL.",
            ),
          );
        }
      } catch (err) {
        clearAuditInFlight(websiteId);
        setFailed(true);
        const fallback = isApiError(err)
          ? err.message
          : "Audit failed. Check the URL and try again.";
        setError(toUserFacingError(err, fallback));
      }
    })();
  }, [websiteId, createAudit, router]);

  // Drive UI from live GET /audits/{id} polling.
  React.useEffect(() => {
    if (!auditId || !websiteId || failed || blockedDuplicate) return;
    const data = auditStatus.data;
    if (!data) return;

    if (isTerminalAuditStatus(data.status)) {
      clearAuditInFlight(websiteId);
      if (isSuccessfulAuditStatus(data.status)) {
        setCompletedAuditForWebsite(websiteId, auditId);
        router.replace(reportPath(auditId));
        return;
      }
      setFailed(true);
      setError(
        toUserFacingError(
          data.failure_message || data.status,
          "The audit did not finish successfully. Try again or use another URL.",
        ),
      );
    }
  }, [
    auditId,
    websiteId,
    auditStatus.data,
    failed,
    blockedDuplicate,
    router,
  ]);

  function retrySameSite() {
    if (!websiteId) return;
    clearAuditInFlight(websiteId);
    setBlockedDuplicate(false);
    setFailed(false);
    setError(null);
    setAuditId(null);
    started.current = false;
    setWebsiteId(null);
    window.setTimeout(() => setWebsiteId(websiteId), 0);
  }

  const poll = auditStatus.data;
  const progress = Math.max(0, Math.min(100, poll?.progress ?? (auditId ? 2 : 0)));
  const currentEngineKey = poll?.current_engine ?? null;
  const currentEngine = engineLabel(currentEngineKey);
  const activeIndex = (() => {
    const idx = engineIndexFor(currentEngineKey);
    if (idx >= 0) return idx;
    if (progress >= 100) return PIPELINE_ENGINES.length;
    if (auditId) return 0;
    return 0;
  })();

  if (!websiteUrl || !websiteId) {
    return (
      <AuditShell status="Preparing…">
        <div className="flex min-h-[50dvh] items-center justify-center">
          <Spinner size="lg" label="Loading analysis" />
        </div>
      </AuditShell>
    );
  }

  const host = displayHost(websiteUrl);
  const completedCount = Math.min(activeIndex, PIPELINE_ENGINES.length);
  const remainingCount = Math.max(
    PIPELINE_ENGINES.length - completedCount - (failed ? 0 : 1),
    0,
  );
  const shellStatus = failed
    ? "Failed"
    : isSuccessfulAuditStatus(poll?.status ?? "")
      ? "Complete"
      : "Analyzing…";

  return (
    <AuditShell status={shellStatus}>
      <Section spacing="md" className="relative">
        <div
          className="pointer-events-none absolute inset-0 bg-[radial-gradient(ellipse_50%_30%_at_50%_0%,var(--color-accent-muted),transparent_65%)]"
          aria-hidden
        />
        <Container className="relative max-w-3xl">
          <motion.div
            initial={reduceMotion ? false : { opacity: 0, y: 10 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: ANIMATIONS.base / 1000, ease: EASE_OUT }}
            className="space-y-6 md:space-y-8"
          >
            <div className="space-y-2 md:space-y-3">
              <Badge variant={failed ? "critical" : "accent"} className="w-fit">
                {failed ? "Audit failed" : "Live analysis"}
              </Badge>
              <Heading level="h1" className="text-2xl md:text-3xl">
                Analyzing {host}
              </Heading>
              <Text variant="muted" className="break-all font-mono text-sm">
                {websiteUrl}
              </Text>
            </div>

            {error ? (
              <div className="space-y-3 rounded-lg border border-danger/30 bg-danger/5 p-4" role="alert">
                <Text className="text-sm text-danger">{error}</Text>
                <div className="flex flex-wrap gap-2">
                  <Button type="button" variant="secondary" onClick={retrySameSite}>
                    Retry this site
                  </Button>
                  <Button type="button" variant="secondary" onClick={() => router.push(ROUTES.audit)}>
                    Try another URL
                  </Button>
                </div>
              </div>
            ) : (
              <>
                <div className="space-y-3" aria-live="polite" aria-atomic="true">
                  <div className="flex flex-wrap items-end justify-between gap-2">
                    <div className="min-w-0">
                      <p className="text-xs uppercase tracking-[0.12em] text-foreground-subtle">
                        Current engine
                      </p>
                      <p className="mt-1 truncate text-sm font-medium text-foreground">
                        {createAudit.isPending && !auditId ? "Starting audit…" : currentEngine}
                      </p>
                    </div>
                    <p className="text-2xl font-semibold tabular-nums text-foreground">
                      {Math.round(progress)}%
                    </p>
                  </div>
                  <Progress
                    value={progress}
                    label={`Analysis progress ${Math.round(progress)} percent`}
                    size="lg"
                  />
                  <p className="text-sm text-foreground-muted">
                    {auditId
                      ? "Live progress from the SitePilot engine pipeline…"
                      : "Creating audit…"}
                  </p>
                </div>

                <div className="grid grid-cols-3 gap-2 sm:gap-3">
                  <Stat label="Completed" value={String(completedCount)} />
                  <Stat label="Remaining" value={String(remainingCount)} />
                  <Stat label="Engines" value={String(PIPELINE_ENGINES.length)} />
                </div>

                <Card>
                  <CardHeader className="pb-2">
                    <CardTitle className="text-base">Engine timeline</CardTitle>
                  </CardHeader>
                  <CardContent>
                    <EngineTimeline activeIndex={activeIndex} failed={failed} />
                  </CardContent>
                </Card>
              </>
            )}
          </motion.div>
        </Container>
      </Section>
    </AuditShell>
  );
}

function Stat({ label, value }: { label: string; value: string }) {
  return (
    <div className="rounded-lg border border-border bg-surface px-3 py-3 sm:px-4">
      <p className="text-[11px] text-foreground-subtle sm:text-xs">{label}</p>
      <p className="mt-1 text-lg font-semibold tabular-nums text-foreground sm:text-xl">
        {value}
      </p>
    </div>
  );
}

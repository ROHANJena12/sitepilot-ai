"use client";

import * as React from "react";
import { AnimatePresence, motion, useReducedMotion } from "framer-motion";
import { ChevronDown, ChevronRight } from "lucide-react";

import { ANIMATIONS, EASE_OUT } from "@/shared/constants/animations";
import { isApiError } from "@/shared/types/api";
import { toUserFacingError } from "@/shared/lib/user-facing-error";
import type { AiResponse, GenerationJob } from "@/shared/types/ai";
import { cn } from "@/shared/lib/utils";
import { Button } from "@/shared/ui/buttons";
import { Badge, Spinner } from "@/shared/ui/feedback";
import { Text } from "@/shared/ui/typography";

type AiPanelProps = {
  title?: string;
  onGenerate: (onProgress?: (job: GenerationJob) => void) => Promise<AiResponse>;
  onRegenerate?: () => Promise<AiResponse>;
  initial?: AiResponse | null;
  /**
   * `embedded` — flush footer inside a finding card (no outer chrome).
   * `standalone` — bordered block for summaries / other surfaces.
   */
  variant?: "embedded" | "standalone";
};

type ResultSection = {
  label: string;
  content: string;
};

const FIELD_LABELS: Record<string, string> = {
  explanation: "Explanation",
  why_it_matters: "Why it matters",
  suggested_fix_summary: "Recommendation",
  summary: "Summary",
  executive_summary: "Executive summary",
  business_summary: "Business summary",
  narrative: "Narrative",
  headline: "Headline",
};

function resultSections(response: AiResponse | null): ResultSection[] {
  if (!response?.result || typeof response.result !== "object") return [];
  const r = response.result as Record<string, unknown>;
  const preferred = [
    "explanation",
    "suggested_fix_summary",
    "why_it_matters",
    "summary",
    "executive_summary",
    "business_summary",
    "narrative",
    "headline",
  ];
  const sections: ResultSection[] = [];
  for (const key of preferred) {
    const value = r[key];
    if (typeof value === "string" && value.trim()) {
      sections.push({
        label: FIELD_LABELS[key] ?? key,
        content: value.trim(),
      });
    }
  }
  if (!sections.length) {
    const first = Object.values(r).find(
      (v) => typeof v === "string" && (v as string).length > 40,
    );
    if (typeof first === "string") {
      sections.push({ label: "Explanation", content: first });
    }
  }
  return sections;
}

function formatGeneratedAt(iso: string): string {
  try {
    return new Date(iso).toLocaleString(undefined, {
      day: "numeric",
      month: "short",
      year: "numeric",
      hour: "2-digit",
      minute: "2-digit",
    });
  } catch {
    return iso;
  }
}

export function AiExplainPanel({
  title = "Explain this finding",
  onGenerate,
  onRegenerate,
  initial = null,
  variant = "standalone",
}: AiPanelProps) {
  const reduceMotion = useReducedMotion();
  const [response, setResponse] = React.useState<AiResponse | null>(initial);
  const [error, setError] = React.useState<string | null>(null);
  const [loading, setLoading] = React.useState(false);
  const [progress, setProgress] = React.useState<GenerationJob | null>(null);
  /** Accordion open state — independent per instance; content is never discarded. */
  const [open, setOpen] = React.useState(false);
  const inFlight = React.useRef(false);

  async function run(mode: "generate" | "regenerate") {
    if (inFlight.current) return;
    inFlight.current = true;
    setLoading(true);
    setError(null);
    setProgress(null);
    try {
      const data =
        mode === "regenerate" && onRegenerate
          ? await onRegenerate()
          : await onGenerate((job) => setProgress(job));
      setResponse(data);
      // Keep accordion open after generate/regenerate so the user sees the result.
      setOpen(true);
    } catch (err) {
      setError(
        toUserFacingError(
          isApiError(err) ? err.message : err instanceof Error ? err.message : err,
          "AI generation failed. Please try again.",
        ),
      );
      setOpen(true);
    } finally {
      inFlight.current = false;
      setLoading(false);
      setProgress(null);
    }
  }

  const sections = resultSections(response);
  const duration = (ANIMATIONS.base + 20) / 1000; // ~220ms
  const headerLabel = response ? "AI Explanation" : title;

  const motionProps = reduceMotion
    ? {
        initial: false as const,
        animate: { height: "auto", opacity: 1 },
        exit: { height: 0, opacity: 0 },
        transition: { duration: 0 },
      }
    : {
        initial: { height: 0, opacity: 0 },
        animate: { height: "auto", opacity: 1 },
        exit: { height: 0, opacity: 0 },
        transition: { duration, ease: EASE_OUT },
      };

  return (
    <div
      className={cn(
        variant === "standalone" &&
          "rounded-lg border border-border/80 bg-surface-muted/30 p-3 md:p-4",
      )}
    >
      {/* Accordion header — sole control for open/close once content exists;
          before generation, header is visual only and Generate starts the flow. */}
      <div className="flex flex-wrap items-center justify-between gap-2">
        {response ? (
          <button
            type="button"
            className="group flex min-w-0 flex-1 items-center gap-2 rounded-md py-0.5 text-left text-sm font-medium text-foreground transition-colors hover:text-accent focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-accent focus-visible:ring-offset-2 focus-visible:ring-offset-bg"
            aria-expanded={open}
            onClick={() => setOpen((prev) => !prev)}
          >
            {open ? (
              <ChevronDown
                className="h-4 w-4 shrink-0 text-foreground-muted transition-transform duration-base group-hover:text-accent"
                aria-hidden
              />
            ) : (
              <ChevronRight
                className="h-4 w-4 shrink-0 text-foreground-muted transition-transform duration-base group-hover:text-accent"
                aria-hidden
              />
            )}
            <span className="truncate">{headerLabel}</span>
          </button>
        ) : (
          <p className="flex min-w-0 flex-1 items-center gap-2 text-sm font-medium text-foreground">
            <ChevronRight className="h-4 w-4 shrink-0 text-foreground-muted" aria-hidden />
            <span className="truncate">{headerLabel}</span>
          </p>
        )}

        {!response ? (
          <Button
            type="button"
            size="sm"
            variant="secondary"
            loading={loading}
            disabled={loading}
            onClick={() => void run("generate")}
          >
            Generate
          </Button>
        ) : null}
      </div>

      {!response && loading ? (
        <div className="mt-3 flex items-center gap-2 text-sm text-foreground-muted">
          <Spinner size="sm" label="Generating" />
          <span>
            {progress
              ? `${progress.status} · ${progress.progress}%${
                  progress.current_phase ? ` · ${progress.current_phase}` : ""
                }`
              : "Generating…"}
          </span>
        </div>
      ) : null}

      {!response && error ? (
        <div className="mt-3 space-y-2" role="alert">
          <Text variant="muted" className="text-sm text-danger">
            {error}
          </Text>
          <Button
            type="button"
            size="sm"
            variant="secondary"
            disabled={loading}
            onClick={() => void run("generate")}
          >
            Retry
          </Button>
        </div>
      ) : null}

      {response ? (
        <>
          <AnimatePresence initial={false}>
            {open ? (
              <motion.div
                key="ai-explanation-body"
                className="overflow-hidden"
                {...motionProps}
              >
                <div className="space-y-3 pt-3">
                  <div
                    className={cn(
                      "rounded-lg border border-border bg-surface p-4 shadow-sm",
                      "ring-1 ring-black/[0.03] dark:ring-white/[0.04]",
                    )}
                  >
                    <div className="space-y-3">
                      <div className="space-y-2">
                        <p className="text-[11px] font-semibold uppercase tracking-[0.14em] text-foreground-subtle">
                          AI Summary
                        </p>
                        <div className="flex flex-wrap gap-1.5">
                          {response.quality?.provider ? (
                            <Badge variant="neutral" size="sm">
                              {response.quality.provider}
                            </Badge>
                          ) : null}
                          {response.quality?.model ? (
                            <Badge variant="neutral" size="sm">
                              {response.quality.model}
                            </Badge>
                          ) : null}
                          {response.quality?.cache_hit ? (
                            <Badge variant="info" size="sm">
                              Cache
                            </Badge>
                          ) : null}
                        </div>
                      </div>

                      <div className="border-t border-border/80" />

                      {loading ? (
                        <div className="flex items-center gap-2 text-sm text-foreground-muted">
                          <Spinner size="sm" label="Generating" />
                          <span>
                            {progress
                              ? `${progress.status} · ${progress.progress}%`
                              : "Regenerating…"}
                          </span>
                        </div>
                      ) : null}

                      {error ? (
                        <Text variant="muted" className="text-sm text-danger" role="alert">
                          {error}
                        </Text>
                      ) : null}

                      {!loading && sections.length ? (
                        <div className="space-y-3.5">
                          {sections.map((section) => (
                            <div key={section.label} className="space-y-1">
                              <p className="text-xs font-semibold text-foreground">
                                {section.label}
                              </p>
                              <p className="text-sm leading-relaxed text-foreground-muted">
                                {section.content}
                              </p>
                            </div>
                          ))}
                        </div>
                      ) : null}

                      {!loading && !sections.length ? (
                        <pre className="overflow-x-auto rounded-md bg-bg p-2.5 text-xs text-foreground-muted">
                          {JSON.stringify(response.result, null, 2)}
                        </pre>
                      ) : null}

                      {response.generated_at ? (
                        <p className="pt-1 text-[11px] tabular-nums text-foreground-subtle">
                          Generated {formatGeneratedAt(response.generated_at)}
                        </p>
                      ) : null}
                    </div>
                  </div>

                  <div className="flex flex-wrap gap-2">
                    <Button
                      type="button"
                      size="sm"
                      variant="ghost"
                      disabled={loading}
                      onClick={() => setOpen(false)}
                    >
                      Hide explanation
                    </Button>
                    {onRegenerate ? (
                      <Button
                        type="button"
                        size="sm"
                        variant="secondary"
                        loading={loading}
                        disabled={loading}
                        onClick={() => void run("regenerate")}
                      >
                        Regenerate
                      </Button>
                    ) : null}
                  </div>
                </div>
              </motion.div>
            ) : null}
          </AnimatePresence>

          {/* When collapsed after an error during regenerate, surface a compact hint */}
          {!open && loading ? (
            <div className="mt-2 flex items-center gap-2 text-sm text-foreground-muted">
              <Spinner size="sm" label="Generating" />
              <span>Regenerating…</span>
            </div>
          ) : null}
        </>
      ) : null}
    </div>
  );
}

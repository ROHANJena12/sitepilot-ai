"use client";

import * as React from "react";
import { AnimatePresence, motion, useReducedMotion } from "framer-motion";
import { Check, Loader2, Circle, X } from "lucide-react";

import { cn } from "@/shared/lib/utils";
import { ANIMATIONS } from "@/shared/constants/animations";
import {
  PIPELINE_ENGINES,
  type EngineStepStatus,
} from "../model/pipeline-engines";

type EngineTimelineProps = {
  /** Index of the active engine, or engines.length when complete */
  activeIndex: number;
  failed?: boolean;
  engines?: ReadonlyArray<{ key: string; label: string }>;
};

function statusFor(
  index: number,
  activeIndex: number,
  failed: boolean,
  total: number,
): EngineStepStatus {
  if (failed && index === Math.min(activeIndex, total - 1) && activeIndex < total) {
    return "failed";
  }
  if (index < activeIndex) return "complete";
  if (index === activeIndex && activeIndex < total) return "active";
  if (activeIndex >= total) return "complete";
  return "pending";
}

export function EngineTimeline({
  activeIndex,
  failed = false,
  engines = PIPELINE_ENGINES,
}: EngineTimelineProps) {
  const reduceMotion = useReducedMotion();
  const activeRef = React.useRef<HTMLLIElement | null>(null);
  const total = engines.length;

  React.useEffect(() => {
    if (reduceMotion) return;
    activeRef.current?.scrollIntoView({ block: "nearest", behavior: "smooth" });
  }, [activeIndex, reduceMotion]);

  return (
    <ol
      className="max-h-[min(28rem,55vh)] space-y-0.5 overflow-y-auto overscroll-contain pr-1"
      aria-label="Analysis engine timeline"
    >
      {engines.map((engine, index) => {
        const status = statusFor(index, activeIndex, failed, total);
        const isActive = status === "active";
        return (
          <li
            key={engine.key}
            ref={isActive ? activeRef : undefined}
            aria-current={isActive ? "step" : undefined}
            className={cn(
              "flex items-center gap-3 rounded-md px-3 py-2 text-sm transition-colors duration-fast",
              status === "active" && "bg-accent-muted text-foreground",
              status === "complete" && "text-foreground-muted",
              status === "pending" && "text-foreground-subtle",
              status === "failed" && "bg-danger/10 text-danger",
            )}
          >
            <span className="flex h-5 w-5 shrink-0 items-center justify-center" aria-hidden>
              <AnimatePresence mode="wait" initial={false}>
                {status === "complete" ? (
                  <motion.span
                    key="done"
                    initial={reduceMotion ? false : { opacity: 0 }}
                    animate={{ opacity: 1 }}
                    exit={{ opacity: 0 }}
                    transition={{ duration: ANIMATIONS.fast / 1000 }}
                    className="flex h-5 w-5 items-center justify-center rounded-pill bg-success/15 text-success"
                  >
                    <Check className="h-3.5 w-3.5" strokeWidth={2.5} />
                  </motion.span>
                ) : status === "failed" ? (
                  <span className="flex h-5 w-5 items-center justify-center rounded-pill bg-danger/15 text-danger">
                    <X className="h-3.5 w-3.5" strokeWidth={2.5} />
                  </span>
                ) : status === "active" ? (
                  <motion.span
                    key="active"
                    initial={reduceMotion ? false : { opacity: 0 }}
                    animate={{ opacity: 1 }}
                    exit={{ opacity: 0 }}
                    transition={{ duration: ANIMATIONS.fast / 1000 }}
                  >
                    <Loader2 className="h-4 w-4 animate-spin text-accent motion-reduce:animate-none" />
                  </motion.span>
                ) : (
                  <Circle className="h-3.5 w-3.5 text-border-strong" strokeWidth={2} />
                )}
              </AnimatePresence>
            </span>
            <span
              className={cn(
                "min-w-0 flex-1 font-medium",
                status === "active" && "text-foreground",
              )}
            >
              {engine.label}
            </span>
            {status === "active" ? (
              <span className="shrink-0 text-[11px] font-medium uppercase tracking-wider text-accent">
                Running
              </span>
            ) : null}
          </li>
        );
      })}
    </ol>
  );
}

"use client";

import * as React from "react";
import { motion, useReducedMotion } from "framer-motion";

import { cn } from "@/shared/lib/utils";
import { ANIMATIONS, EASE_OUT } from "@/shared/constants/animations";

export type RevealProps = {
  children: React.ReactNode;
  className?: string;
  delay?: number;
  /** Vertical offset in px. Prefer ≤12 for calm motion. */
  y?: number;
  once?: boolean;
};

/**
 * Reduced-motion-aware entrance. Opacity + slight translate only.
 * Keep delays small (≤0.12s) when staggering lists.
 */
export function Reveal({
  className,
  children,
  delay = 0,
  y = 10,
  once = true,
}: RevealProps) {
  const reduceMotion = useReducedMotion();

  if (reduceMotion) {
    return <div className={className}>{children}</div>;
  }

  return (
    <motion.div
      className={cn(className)}
      initial={{ opacity: 0, y }}
      whileInView={{ opacity: 1, y: 0 }}
      viewport={{ once, margin: "-48px" }}
      transition={{
        duration: ANIMATIONS.slow / 1000,
        delay: Math.min(delay, 0.16),
        ease: EASE_OUT,
      }}
    >
      {children}
    </motion.div>
  );
}

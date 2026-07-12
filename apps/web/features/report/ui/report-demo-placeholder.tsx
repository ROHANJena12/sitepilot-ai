"use client";

import Link from "next/link";
import { motion, useReducedMotion } from "framer-motion";
import { ArrowLeft, FileBarChart2 } from "lucide-react";

import { ROUTES } from "@/shared/constants/routes";
import { ANIMATIONS } from "@/shared/constants/animations";
import { Button } from "@/shared/ui/buttons";
import { Container, Section } from "@/shared/ui/layout";
import { Heading, Text } from "@/shared/ui/typography";
import { AuditShell } from "@/features/audit/ui/audit-shell";

/**
 * Placeholder only — full report dashboard is intentionally not built here.
 */
export function ReportDemoPlaceholder() {
  const reduceMotion = useReducedMotion();

  return (
    <AuditShell status="Demo report">
      <Section spacing="lg" className="relative overflow-hidden">
        <div
          className="pointer-events-none absolute inset-0 bg-[radial-gradient(ellipse_70%_50%_at_50%_20%,var(--color-accent-muted),transparent_65%)]"
          aria-hidden
        />
        <Container className="relative flex min-h-[70dvh] flex-col items-center justify-center text-center">
          <motion.div
            initial={reduceMotion ? false : { opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: ANIMATIONS.slow / 1000 }}
            className="flex max-w-lg flex-col items-center"
          >
            <div
              className="relative mb-10 flex h-40 w-40 items-center justify-center"
              aria-hidden
            >
              <div className="absolute inset-0 rounded-xl border border-border bg-surface shadow-md" />
              <div className="absolute -right-3 -top-3 h-24 w-20 rotate-6 rounded-lg border border-border bg-bg-subtle" />
              <div className="absolute -left-4 bottom-2 h-16 w-28 -rotate-3 rounded-lg border border-accent/30 bg-accent-muted" />
              <FileBarChart2 className="relative h-14 w-14 text-accent" strokeWidth={1.5} />
              {!reduceMotion ? (
                <motion.span
                  className="absolute -bottom-2 left-1/2 h-1 w-16 -translate-x-1/2 rounded-pill bg-accent/50"
                  animate={{ opacity: [0.3, 0.8, 0.3], scaleX: [0.85, 1, 0.85] }}
                  transition={{ duration: 2.4, repeat: Infinity, ease: "easeInOut" }}
                />
              ) : null}
            </div>

            <Heading level="h1" className="text-2xl md:text-3xl">
              Sample report preview
            </Heading>
            <Text variant="muted" className="mt-3">
              Live reports include overall health, category scores, findings,
              recommendations, export, and read-only sharing. Run an audit on a
              public URL to generate yours.
            </Text>

            <div className="mt-8 flex flex-col gap-3 sm:flex-row">
              <Button asChild>
                <Link href={ROUTES.audit}>
                  Analyze a website
                </Link>
              </Button>
              <Button asChild variant="secondary">
                <Link href={ROUTES.home}>
                  <ArrowLeft className="h-4 w-4" aria-hidden />
                  Back to home
                </Link>
              </Button>
            </div>
          </motion.div>
        </Container>
      </Section>
    </AuditShell>
  );
}

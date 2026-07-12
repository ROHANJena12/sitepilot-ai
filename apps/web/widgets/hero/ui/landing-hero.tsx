"use client";

import * as React from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { motion, useReducedMotion } from "framer-motion";
import { ArrowRight } from "lucide-react";

import { siteConfig } from "@/shared/config/site";
import { ROUTES } from "@/shared/constants/routes";
import { ANIMATIONS, EASE_OUT } from "@/shared/constants/animations";
import { useStartAuditFromUrl } from "@/shared/hooks/useAudit";
import { toUserFacingError } from "@/shared/lib/user-facing-error";
import { isApiError } from "@/shared/types/api";
import { Button } from "@/shared/ui/buttons";
import { Input } from "@/shared/ui/forms";
import { Container } from "@/shared/ui/layout";
import { Heading, Text } from "@/shared/ui/typography";

function HeroAtmosphere() {
  const reduceMotion = useReducedMotion();

  return (
    <div
      className="pointer-events-none absolute inset-0 overflow-hidden"
      aria-hidden
    >
      <div className="absolute inset-0 bg-[radial-gradient(ellipse_80%_60%_at_50%_-10%,var(--color-accent-muted),transparent_55%)]" />
      <div className="absolute inset-0 bg-[linear-gradient(to_bottom,transparent_40%,var(--color-bg)_95%)]" />
      <div
        className="absolute inset-0 opacity-[0.35]"
        style={{
          backgroundImage:
            "linear-gradient(var(--color-border) 1px, transparent 1px), linear-gradient(90deg, var(--color-border) 1px, transparent 1px)",
          backgroundSize: "64px 64px",
          maskImage: "radial-gradient(ellipse at center, black 20%, transparent 70%)",
        }}
      />
      {!reduceMotion ? (
        <>
          <motion.div
            className="absolute -left-24 top-24 h-64 w-64 rounded-full bg-accent/10 blur-3xl"
            animate={{ x: [0, 24, 0], y: [0, 16, 0], opacity: [0.3, 0.45, 0.3] }}
            transition={{ duration: 16, repeat: Infinity, ease: "easeInOut" }}
          />
          <motion.div
            className="absolute -right-16 bottom-10 h-72 w-72 rounded-full bg-info/10 blur-3xl"
            animate={{ x: [0, -20, 0], y: [0, -12, 0], opacity: [0.2, 0.35, 0.2] }}
            transition={{ duration: 20, repeat: Infinity, ease: "easeInOut" }}
          />
        </>
      ) : null}
    </div>
  );
}

/**
 * Full-bleed marketing hero — brand-forward first viewport.
 * URL + Analyze starts the live audit immediately (same validation/API as /audit).
 * Primary CTA still navigates to /audit.
 */
export function LandingHero() {
  const router = useRouter();
  const reduceMotion = useReducedMotion();
  const startAudit = useStartAuditFromUrl();
  const [url, setUrl] = React.useState("https://");
  const [error, setError] = React.useState<string | null>(null);
  const inFlight = React.useRef(false);

  async function onSubmit(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (inFlight.current || startAudit.isPending) return;
    inFlight.current = true;
    setError(null);
    try {
      const result = await startAudit.mutateAsync(url);
      router.push(result.href);
    } catch (err) {
      setError(
        toUserFacingError(
          err,
          isApiError(err)
            ? err.message
            : "Could not start the audit. Check the URL and try again.",
        ),
      );
    } finally {
      inFlight.current = false;
    }
  }

  const busy = startAudit.isPending;
  const motionProps = reduceMotion
    ? {}
    : {
        initial: { opacity: 0, y: 12 },
        animate: { opacity: 1, y: 0 },
        transition: { duration: ANIMATIONS.slow / 1000, ease: EASE_OUT },
      };

  return (
    <section className="relative isolate min-h-[min(100dvh,56rem)] overflow-hidden">
      <HeroAtmosphere />
      <Container className="relative flex min-h-[min(100dvh-4rem,52rem)] flex-col justify-center py-14 md:py-20">
        <motion.div className="max-w-3xl" {...motionProps}>
          <p className="mb-4 text-sm font-medium tracking-[0.08em] text-accent md:text-base">
            {siteConfig.name}
          </p>
          <Heading level="display" className="max-w-[18ch]">
            Website intelligence, not another score dump.
          </Heading>
          <Text className="mt-5 max-w-xl text-foreground-muted md:text-lg">
            Turn SEO, performance, security, and accessibility findings into a
            clear priority list — with AI recommendations that speak business,
            not jargon.
          </Text>

          <div className="mt-8 flex flex-col gap-3 sm:flex-row sm:items-center">
            <Button asChild size="lg" className="w-full sm:w-auto">
              <Link href={ROUTES.audit}>
                Analyze my website
                <ArrowRight className="h-4 w-4" aria-hidden />
              </Link>
            </Button>
            <Button asChild variant="secondary" size="lg" className="w-full sm:w-auto">
              <Link href={ROUTES.reportDemo}>View sample report</Link>
            </Button>
          </div>

          <form
            onSubmit={(event) => void onSubmit(event)}
            className="mt-8 flex w-full max-w-xl flex-col gap-3 sm:flex-row sm:items-stretch"
            aria-label="Try with a website URL"
            noValidate
          >
            <label htmlFor="hero-url" className="sr-only">
              Website URL
            </label>
            <Input
              id="hero-url"
              name="url"
              type="url"
              inputMode="url"
              autoComplete="url"
              placeholder="https://yourwebsite.com"
              value={url}
              error={Boolean(error)}
              aria-invalid={Boolean(error) || undefined}
              aria-describedby={error ? "hero-url-error" : undefined}
              disabled={busy}
              onChange={(event) => {
                setUrl(event.target.value);
                if (error) setError(null);
              }}
              size="lg"
              className="min-h-11 sm:flex-1"
            />
            <Button
              type="submit"
              size="lg"
              variant="secondary"
              loading={busy}
              disabled={busy}
              className="shrink-0 sm:min-w-[7.5rem]"
            >
              Analyze
            </Button>
          </form>

          {error ? (
            <p id="hero-url-error" role="alert" className="mt-3 max-w-xl text-sm text-danger">
              {error}
            </p>
          ) : null}

          <p className="mt-8 text-xs text-foreground-subtle md:text-sm">
            <span>No credit card required</span>
            <span className="mx-2 text-border-strong" aria-hidden>
              ·
            </span>
            <span>Public URLs only</span>
            <span className="mx-2 text-border-strong" aria-hidden>
              ·
            </span>
            <span>Privacy-first analysis</span>
          </p>
        </motion.div>
      </Container>
    </section>
  );
}

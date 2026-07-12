"use client";

import * as React from "react";
import { useRouter, useSearchParams } from "next/navigation";
import { motion, useReducedMotion } from "framer-motion";
import { ArrowRight, Clock, Globe } from "lucide-react";

import { ANIMATIONS, EASE_OUT } from "@/shared/constants/animations";
import { useCreateWebsite } from "@/shared/hooks/useAudit";
import { isApiError } from "@/shared/types/api";
import { Button } from "@/shared/ui/buttons";
import { Input, Label } from "@/shared/ui/forms";
import { Badge } from "@/shared/ui/feedback";
import { Card, CardContent, CardHeader, CardTitle } from "@/shared/ui/cards";
import { Container, Section } from "@/shared/ui/layout";
import { Heading, Text } from "@/shared/ui/typography";
import { cn } from "@/shared/lib/utils";

import {
  getRecentUrls,
  type RecentAuditView,
} from "../lib/audit-session";
import { buildAnalyzingHref, rememberAuditHandoff, validateForAudit } from "../lib/begin-audit";
import { EXAMPLE_URLS } from "../model/url-validation";
import { AuditShell } from "./audit-shell";

export function AuditInputPage() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const reduceMotion = useReducedMotion();
  const createWebsite = useCreateWebsite();
  const [url, setUrl] = React.useState("https://");
  const [error, setError] = React.useState<string | null>(null);
  const [recent, setRecent] = React.useState<RecentAuditView[]>([]);

  React.useEffect(() => {
    const fromQuery = searchParams.get("url");
    if (fromQuery) {
      setUrl(fromQuery.startsWith("http") ? fromQuery : `https://${fromQuery}`);
    }
    setRecent(getRecentUrls());
  }, [searchParams]);

  function applyExample(example: string) {
    setUrl(example);
    setError(null);
  }

  async function onSubmit(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const result = validateForAudit(url);
    if (!result.ok) {
      setError(result.message);
      return;
    }

    setError(null);
    try {
      const website = await createWebsite.mutateAsync(result.normalized);
      rememberAuditHandoff(website.id, result.normalized);
      router.push(
        buildAnalyzingHref({
          websiteId: website.id,
          url: result.normalized,
        }),
      );
    } catch (err) {
      setError(isApiError(err) ? err.message : "Could not register website");
    }
  }

  return (
    <AuditShell>
      <a href="#audit-form" className="skip-link">
        Skip to URL form
      </a>
      <Section spacing="md" className="relative overflow-hidden md:py-20">
        <div
          className="pointer-events-none absolute inset-0 bg-[radial-gradient(ellipse_60%_40%_at_50%_0%,var(--color-accent-muted),transparent_70%)]"
          aria-hidden
        />
        <Container className="relative max-w-2xl">
          <motion.div
            initial={reduceMotion ? false : { opacity: 0, y: 10 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: ANIMATIONS.slow / 1000, ease: EASE_OUT }}
          >
            <Heading level="h1">Analyze a website</Heading>
            <Text variant="muted" className="mt-3 max-w-lg">
              Enter a public URL. SitePilot will crawl the site, run analysis engines, and open a
              live report.
            </Text>

            <form
              id="audit-form"
              onSubmit={(e) => void onSubmit(e)}
              className="mt-8 space-y-4 md:mt-10"
              noValidate
            >
              <div className="space-y-2">
                <Label htmlFor="audit-url" size="md">
                  Website URL
                </Label>
                <Input
                  id="audit-url"
                  name="url"
                  type="url"
                  inputMode="url"
                  autoComplete="url"
                  autoFocus
                  size="lg"
                  placeholder="https://yourwebsite.com"
                  value={url}
                  error={Boolean(error)}
                  aria-invalid={Boolean(error) || undefined}
                  aria-describedby={error ? "audit-url-error" : "audit-url-hint"}
                  onChange={(event) => {
                    setUrl(event.target.value);
                    if (error) setError(null);
                  }}
                  className="min-h-11"
                />
                {error ? (
                  <p id="audit-url-error" role="alert" className="text-sm text-danger">
                    {error}
                  </p>
                ) : (
                  <p id="audit-url-hint" className="text-xs text-foreground-subtle">
                    Public http(s) sites only. Creates a website record, then runs the full audit.
                  </p>
                )}
              </div>

              <Button
                type="submit"
                size="lg"
                loading={createWebsite.isPending}
                className="w-full sm:w-auto"
                rightIcon={
                  createWebsite.isPending ? undefined : (
                    <ArrowRight className="h-4 w-4" aria-hidden />
                  )
                }
              >
                Analyze Website
              </Button>
            </form>

            <div className="mt-8">
              <Text
                variant="caption"
                className="uppercase tracking-[0.12em] text-foreground-subtle"
              >
                Try an example
              </Text>
              <ul className="mt-3 flex flex-wrap gap-2">
                {EXAMPLE_URLS.map((example) => (
                  <li key={example}>
                    <button
                      type="button"
                      onClick={() => applyExample(example)}
                      className={cn(
                        "rounded-md focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-accent focus-visible:ring-offset-2 focus-visible:ring-offset-bg",
                      )}
                    >
                      <Badge
                        variant="neutral"
                        className="cursor-pointer transition-colors duration-fast hover:border-border-strong hover:bg-surface-hover"
                      >
                        {example.replace(/^https?:\/\//, "")}
                      </Badge>
                    </button>
                  </li>
                ))}
              </ul>
            </div>

            {recent.length > 0 ? (
              <Card className="mt-8 md:mt-10">
                <CardHeader className="pb-3">
                  <CardTitle className="flex flex-wrap items-center gap-2 text-base">
                    <Clock className="h-4 w-4 text-foreground-muted" aria-hidden />
                    Recently analyzed
                  </CardTitle>
                </CardHeader>
                <CardContent className="pt-0">
                  <ul className="divide-y divide-border">
                    {recent.map((item) => (
                      <li key={item.url}>
                        <button
                          type="button"
                          onClick={() => applyExample(item.url)}
                          className="flex w-full items-center justify-between gap-4 rounded-md py-3 text-left transition-colors duration-fast hover:text-accent focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-accent focus-visible:ring-offset-2 focus-visible:ring-offset-bg"
                        >
                          <span className="flex min-w-0 items-center gap-2">
                            <Globe
                              className="h-4 w-4 shrink-0 text-foreground-subtle"
                              aria-hidden
                            />
                            <span className="truncate text-sm font-medium">{item.label}</span>
                          </span>
                          <span className="shrink-0 text-xs text-foreground-subtle">
                            {item.when}
                          </span>
                        </button>
                      </li>
                    ))}
                  </ul>
                </CardContent>
              </Card>
            ) : null}
          </motion.div>
        </Container>
      </Section>
    </AuditShell>
  );
}

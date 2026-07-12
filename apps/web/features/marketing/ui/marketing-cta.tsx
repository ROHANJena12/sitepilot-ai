import Link from "next/link";
import { ArrowRight } from "lucide-react";

import { ROUTES } from "@/shared/constants/routes";
import { Reveal } from "@/shared/ui/motion";
import { Button } from "@/shared/ui/buttons";
import { Container, Section } from "@/shared/ui/layout";
import { Heading, Text } from "@/shared/ui/typography";

type MarketingCtaProps = {
  title?: string;
  description?: string;
  primaryHref?: string;
  primaryLabel?: string;
  secondaryHref?: string;
  secondaryLabel?: string;
};

export function MarketingCta({
  title = "Analyze your website in minutes",
  description = "Paste a URL. Get a prioritized health report with grounded AI explanations — no spreadsheet archaeology required.",
  primaryHref = ROUTES.audit,
  primaryLabel = "Analyze Website",
  secondaryHref = ROUTES.help,
  secondaryLabel = "Help Center",
}: MarketingCtaProps) {
  return (
    <Section spacing="lg" aria-labelledby="marketing-cta-heading">
      <Container>
        <Reveal>
          <div className="relative overflow-hidden rounded-xl border border-border bg-surface px-6 py-14 text-center md:px-12 md:py-16">
            <div
              className="pointer-events-none absolute inset-0 bg-[radial-gradient(ellipse_at_top,var(--color-accent-muted),transparent_60%)]"
              aria-hidden
            />
            <div className="relative mx-auto max-w-2xl">
              <Heading id="marketing-cta-heading" level="h2">
                {title}
              </Heading>
              <Text variant="muted" className="mt-3 md:text-base">
                {description}
              </Text>
              <div className="mt-8 flex flex-col items-center justify-center gap-3 sm:flex-row">
                <Button asChild size="lg">
                  <Link href={primaryHref}>
                    {primaryLabel}
                    <ArrowRight className="h-4 w-4" aria-hidden />
                  </Link>
                </Button>
                <Button asChild variant="secondary" size="lg">
                  <Link href={secondaryHref}>{secondaryLabel}</Link>
                </Button>
              </div>
            </div>
          </div>
        </Reveal>
      </Container>
    </Section>
  );
}

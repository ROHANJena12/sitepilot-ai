import { Reveal } from "@/shared/ui/motion";
import { Container, Section } from "@/shared/ui/layout";
import { Heading, Text } from "@/shared/ui/typography";

type PageHeroProps = {
  id: string;
  eyebrow?: string;
  title: string;
  description: string;
};

/**
 * Compact marketing page hero — brand-aligned atmosphere without a second design system.
 */
export function PageHero({ id, eyebrow, title, description }: PageHeroProps) {
  return (
    <Section
      spacing="lg"
      className="relative overflow-hidden border-b border-border"
      aria-labelledby={id}
    >
      <div
        className="pointer-events-none absolute inset-0 bg-[radial-gradient(ellipse_70%_50%_at_50%_-20%,var(--color-accent-muted),transparent_55%)]"
        aria-hidden
      />
      <div
        className="pointer-events-none absolute inset-0 opacity-[0.28]"
        style={{
          backgroundImage:
            "linear-gradient(var(--color-border) 1px, transparent 1px), linear-gradient(90deg, var(--color-border) 1px, transparent 1px)",
          backgroundSize: "56px 56px",
          maskImage: "radial-gradient(ellipse at center, black 15%, transparent 70%)",
        }}
        aria-hidden
      />
      <Container className="relative">
        <Reveal className="mx-auto max-w-3xl text-center">
          {eyebrow ? (
            <p className="mb-3 text-xs font-medium uppercase tracking-[0.14em] text-accent">
              {eyebrow}
            </p>
          ) : null}
          <Heading id={id} level="h1">
            {title}
          </Heading>
          <Text variant="muted" className="mt-4 text-base md:text-lg">
            {description}
          </Text>
        </Reveal>
      </Container>
    </Section>
  );
}

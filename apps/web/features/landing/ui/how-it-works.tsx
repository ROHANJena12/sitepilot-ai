import { Reveal } from "@/shared/ui/motion";
import { Container, Section } from "@/shared/ui/layout";
import { Heading, Text } from "@/shared/ui/typography";

const STEPS = [
  {
    step: "01",
    title: "Enter URL",
    description: "Paste any public website. We validate the target and prepare a safe crawl.",
  },
  {
    step: "02",
    title: "AI Analysis",
    description:
      "Engines inspect SEO, performance, security, and accessibility in a coordinated pass.",
  },
  {
    step: "03",
    title: "Issue Detection",
    description:
      "Findings are ranked by severity and confidence — not buried in an unsorted checklist.",
  },
  {
    step: "04",
    title: "Actionable Report",
    description:
      "Get a business-ready report: what to fix, why it matters, and what to do next.",
  },
] as const;

export function HowItWorks() {
  return (
    <Section id="how-it-works" spacing="lg" aria-labelledby="how-heading">
      <Container>
        <Reveal className="mx-auto max-w-2xl text-center">
          <Heading id="how-heading" level="h2">
            How it works
          </Heading>
          <Text variant="muted" className="mt-3">
            From URL to prioritized action in four steps — calm, fast, and explainable.
          </Text>
        </Reveal>

        <ol className="relative mx-auto mt-14 max-w-2xl">
          {STEPS.map((item, index) => (
            <li key={item.step} className="relative flex gap-5 pb-10 last:pb-0 md:gap-8">
              {index < STEPS.length - 1 ? (
                <span
                  className="absolute left-[19px] top-10 h-[calc(100%-1.5rem)] w-px bg-border md:left-[23px]"
                  aria-hidden
                />
              ) : null}
              <Reveal delay={index * 0.06} className="flex min-w-0 flex-1 gap-5 md:gap-8">
                <span className="relative z-10 flex h-10 w-10 shrink-0 items-center justify-center rounded-md border border-border bg-surface font-mono text-xs font-medium text-accent md:h-12 md:w-12 md:text-sm">
                  {item.step}
                </span>
                <div className="pt-1.5 md:pt-2">
                  <h3 className="text-lg font-semibold tracking-tight text-foreground">
                    {item.title}
                  </h3>
                  <Text variant="muted" className="mt-1.5 max-w-md">
                    {item.description}
                  </Text>
                </div>
              </Reveal>
            </li>
          ))}
        </ol>
      </Container>
    </Section>
  );
}

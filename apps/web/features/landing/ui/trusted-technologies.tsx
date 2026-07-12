import { Reveal } from "@/shared/ui/motion";
import { Container, Section } from "@/shared/ui/layout";
import { Heading, Text } from "@/shared/ui/typography";

const TECHNOLOGIES = [
  { name: "Next.js", role: "App platform" },
  { name: "FastAPI", role: "API & engines" },
  { name: "PostgreSQL", role: "System of record" },
  { name: "OpenAI", role: "Recommendations" },
  { name: "Lighthouse", role: "Web vitals" },
  { name: "Redis", role: "Job queue" },
] as const;

export function TrustedTechnologies() {
  return (
    <Section spacing="sm" aria-labelledby="tech-heading">
      <Container>
        <Reveal>
          <Text
            id="tech-heading"
            variant="caption"
            className="text-center uppercase tracking-[0.14em] text-foreground-subtle"
          >
            Trusted technologies
          </Text>
        </Reveal>
        <ul className="mt-8 grid grid-cols-2 gap-3 sm:grid-cols-3 lg:grid-cols-6">
          {TECHNOLOGIES.map((tech, index) => (
            <Reveal key={tech.name} delay={index * 0.04}>
              <li className="flex h-full flex-col items-center justify-center gap-1 rounded-lg border border-border bg-surface/60 px-3 py-5 text-center">
                <span className="text-sm font-semibold tracking-tight text-foreground">
                  {tech.name}
                </span>
                <span className="text-[11px] text-foreground-subtle">{tech.role}</span>
              </li>
            </Reveal>
          ))}
        </ul>
        {/* Heading kept for a11y hierarchy without competing with brand hero */}
        <Heading level="h2" className="sr-only">
          Built with modern infrastructure
        </Heading>
      </Container>
    </Section>
  );
}

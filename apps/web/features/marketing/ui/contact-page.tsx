import { Linkedin, Mail } from "lucide-react";

import { siteConfig } from "@/shared/config/site";
import { Reveal } from "@/shared/ui/motion";
import { Card, CardContent, CardHeader, CardTitle } from "@/shared/ui/cards";
import { Container, Section } from "@/shared/ui/layout";
import { Heading, Text } from "@/shared/ui/typography";

import { ContactForm } from "./contact-form";
import { MarketingShell } from "./marketing-shell";
import { PageHero } from "./page-hero";

const CHANNELS = [
  {
    icon: Mail,
    title: "Email",
    body: siteConfig.email,
    href: `mailto:${siteConfig.email}`,
    external: false,
  },
  {
    icon: Linkedin,
    title: "LinkedIn",
    body: "Connect with me on LinkedIn",
    href: "https://www.linkedin.com/in/rohan-jena-589849210/",
    external: true,
  },
] as const;

export function ContactPage() {
  return (
    <MarketingShell labelledBy="contact-hero">
      <PageHero
        id="contact-hero"
        eyebrow="Contact"
        title="Talk with the SitePilot team"
        description="Questions about audits, AI explanations, sharing, or partnerships — reach out. Form delivery is coming soon; email works today."
      />

      <Section spacing="lg" aria-labelledby="contact-channels-heading">
        <Container>
          <Heading id="contact-channels-heading" level="h2" className="sr-only">
            Contact channels
          </Heading>
          <div className="mx-auto grid max-w-2xl gap-4 sm:grid-cols-2">
            {CHANNELS.map((channel, index) => (
              <Reveal key={channel.title} delay={index * 0.05}>
                <a
                  href={channel.href}
                  {...(channel.external
                    ? { target: "_blank", rel: "noopener noreferrer" }
                    : {})}
                  className="block h-full rounded-xl focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-accent focus-visible:ring-offset-2 focus-visible:ring-offset-bg"
                >
                  <Card className="h-full transition-colors hover:bg-surface-hover">
                    <CardHeader>
                      <channel.icon className="h-5 w-5 text-accent" aria-hidden />
                      <CardTitle>{channel.title}</CardTitle>
                    </CardHeader>
                    <CardContent>
                      <Text variant="muted">{channel.body}</Text>
                    </CardContent>
                  </Card>
                </a>
              </Reveal>
            ))}
          </div>

          <div className="mx-auto mt-12 max-w-2xl">
            <Reveal>
              <Heading level="h2" className="mb-6 text-center">
                Send a message
              </Heading>
              <ContactForm />
            </Reveal>
          </div>
        </Container>
      </Section>
    </MarketingShell>
  );
}

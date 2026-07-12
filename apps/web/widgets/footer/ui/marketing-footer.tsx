import Link from "next/link";
import { Github, Linkedin, Mail } from "lucide-react";

import { footerNav, siteConfig } from "@/shared/config/site";
import { BrandLogo } from "@/shared/ui/brand";
import { Container, Section } from "@/shared/ui/layout";
import { Separator } from "@/shared/ui/feedback";
import { Text } from "@/shared/ui/typography";

function FooterColumn({
  title,
  links,
}: {
  title: string;
  links: readonly { label: string; href: string }[];
}) {
  return (
    <div>
      <p className="text-sm font-medium text-foreground">{title}</p>
      <ul className="mt-4 space-y-2.5">
        {links.map((link) => (
          <li key={link.href}>
            <Link
              href={link.href}
              className="text-sm text-foreground-muted transition-colors duration-fast hover:text-foreground focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-accent"
            >
              {link.label}
            </Link>
          </li>
        ))}
      </ul>
    </div>
  );
}

export function MarketingFooter() {
  const year = new Date().getFullYear();

  return (
    <Section
      spacing="md"
      className="border-t border-border bg-bg-subtle"
      aria-labelledby="footer-heading"
    >
      <Container>
        <h2 id="footer-heading" className="sr-only">
          Footer
        </h2>
        <div className="grid gap-10 md:grid-cols-[1.4fr_repeat(3,1fr)]">
          <div className="max-w-sm">
            <BrandLogo />
            <Text variant="muted" className="mt-4">
              {siteConfig.tagline}
            </Text>
            <div className="mt-6 flex items-center gap-3">
              <a
                href={siteConfig.links.github}
                target="_blank"
                rel="noopener noreferrer"
                className="rounded-md p-2 text-foreground-muted transition-colors hover:text-foreground focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-accent"
                aria-label="GitHub"
              >
                <Github className="h-4 w-4" />
              </a>
              <a
                href={siteConfig.links.linkedin}
                target="_blank"
                rel="noopener noreferrer"
                className="rounded-md p-2 text-foreground-muted transition-colors hover:text-foreground focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-accent"
                aria-label="LinkedIn"
              >
                <Linkedin className="h-4 w-4" />
              </a>
              <a
                href={`mailto:${siteConfig.email}`}
                className="rounded-md p-2 text-foreground-muted transition-colors hover:text-foreground focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-accent"
                aria-label={`Email ${siteConfig.email}`}
              >
                <Mail className="h-4 w-4" />
              </a>
            </div>
          </div>

          <FooterColumn title="Product" links={footerNav.product} />
          <FooterColumn title="Company" links={footerNav.company} />
          <FooterColumn title="Legal" links={footerNav.legal} />
        </div>

        <Separator className="my-10" />

        <Text variant="caption" className="text-foreground-subtle">
          © {year} {siteConfig.name}. All rights reserved.
        </Text>
      </Container>
    </Section>
  );
}

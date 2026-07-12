import Link from "next/link";

import { ROUTES } from "@/shared/constants/routes";
import { siteConfig } from "@/shared/config/site";
import { Container, Section } from "@/shared/ui/layout";
import { Text } from "@/shared/ui/typography";

import { MarketingShell } from "./marketing-shell";
import { PageHero } from "./page-hero";
import { Prose } from "./prose";

export function PrivacyPage() {
  return (
    <MarketingShell labelledBy="privacy-hero">
      <PageHero
        id="privacy-hero"
        eyebrow="Legal"
        title="Privacy Policy"
        description="How SitePilot AI collects, uses, and protects information when you use our website intelligence platform."
      />

      <Section spacing="lg" aria-labelledby="privacy-content-heading">
        <Container size="sm">
          <h2 id="privacy-content-heading" className="sr-only">
            Privacy policy content
          </h2>
          <Text variant="caption" className="mb-8 text-foreground-subtle">
            Last updated: July 13, 2026
          </Text>
          <Prose>
            <p>
              This Privacy Policy describes how {siteConfig.name} (“SitePilot”, “we”, “us”)
              handles information in connection with {siteConfig.url} and related services.
              It is written for a production SaaS posture and may be refined as the product
              evolves.
            </p>

            <h2 id="info-collected">Information we collect</h2>
            <p>Depending on how you use SitePilot, we may process:</p>
            <ul>
              <li>
                <strong>Account or contact details</strong> you voluntarily provide (for example
                email when you contact us).
              </li>
              <li>
                <strong>Usage and diagnostic data</strong> such as request metadata, timestamps,
                and error logs needed to operate and secure the service.
              </li>
              <li>
                <strong>Technical identifiers</strong> such as IP address and user-agent when
                connecting to our APIs or website.
              </li>
            </ul>

            <h2 id="audit-urls">Audit URLs</h2>
            <p>
              When you start an audit, you submit a public website URL. We process that URL to
              validate reachability, crawl publicly available resources, and generate findings.
              Do not submit URLs you are not authorized to analyze.
            </p>

            <h2 id="reports">Generated reports</h2>
            <p>
              Audits produce structured reports (scores, findings, recommendations, and related
              metadata). Reports are stored so you can view, export, and — when you choose —
              share them. Shared links use signed, time-limited tokens and are intended for
              read-only access.
            </p>

            <h2 id="ai-processing">AI processing</h2>
            <p>
              Optional AI features explain completed audit artifacts (for example findings or
              summaries). AI providers may receive the grounded context required to generate an
              explanation. SitePilot’s AI layer is designed to explain existing results — not to
              invent new checks or alter engine measurements. Provider selection and retention
              may follow each provider’s own terms.
            </p>

            <h2 id="cookies">Cookies</h2>
            <p>
              We may use essential cookies or local storage for theme preference and session
              continuity. We do not use advertising cookies on the core product surfaces
              described here. If analytics cookies are introduced later, this policy will be
              updated and consent mechanisms added where required.
            </p>

            <h2 id="analytics">Analytics</h2>
            <p>
              Product analytics, if enabled in a given environment, are used to understand
              feature usage and reliability — not to sell personal data. When analytics are
              active, they should be configured to minimize personal identifiers.
            </p>

            <h2 id="third-parties">Third-party providers</h2>
            <p>We may rely on subprocessors for:</p>
            <ul>
              <li>Hosting and infrastructure</li>
              <li>Databases and object storage</li>
              <li>AI model providers (for optional explanations)</li>
              <li>Email or support tooling (when enabled)</li>
            </ul>
            <p>
              Those providers process data only as needed to deliver the service under
              appropriate contractual and security controls.
            </p>

            <h2 id="retention">Data retention</h2>
            <p>
              We retain audit and report data for as long as needed to provide the service,
              comply with legal obligations, resolve disputes, and enforce agreements. Share
              tokens expire according to configured TTL and do not grant indefinite access.
              Operational logs are retained for a limited diagnostic window.
            </p>

            <h2 id="rights">Your rights</h2>
            <p>
              Depending on your location, you may have rights to access, correct, delete, or
              restrict certain personal data, or to object to certain processing. To exercise
              these rights, contact us using the details below. We may need to verify your
              request before acting on it.
            </p>

            <h2 id="security">Security</h2>
            <p>
              We apply industry-standard safeguards such as TLS in transit, access controls,
              SSRF-safe URL validation for audits, and signed tokens for shared reports. No
              method of transmission or storage is perfectly secure; please report suspected
              issues promptly.
            </p>

            <h2 id="children">Children</h2>
            <p>
              SitePilot is directed to business and professional users. We do not knowingly
              collect personal information from children.
            </p>

            <h2 id="changes">Changes</h2>
            <p>
              We may update this policy as the product or legal requirements change. Material
              updates will be reflected by revising the “Last updated” date on this page.
            </p>

            <h2 id="contact">Contact</h2>
            <p>
              Privacy questions:{" "}
              <a href={`mailto:${siteConfig.email}`}>{siteConfig.email}</a>. You can also use
              our <Link href={ROUTES.contact}>Contact</Link> page.
            </p>
          </Prose>
        </Container>
      </Section>
    </MarketingShell>
  );
}

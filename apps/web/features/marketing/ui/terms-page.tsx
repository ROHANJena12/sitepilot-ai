import Link from "next/link";

import { ROUTES } from "@/shared/constants/routes";
import { siteConfig } from "@/shared/config/site";
import { Container, Section } from "@/shared/ui/layout";
import { Text } from "@/shared/ui/typography";

import { MarketingShell } from "./marketing-shell";
import { PageHero } from "./page-hero";
import { Prose } from "./prose";

export function TermsPage() {
  return (
    <MarketingShell labelledBy="terms-hero">
      <PageHero
        id="terms-hero"
        eyebrow="Legal"
        title="Terms & Conditions"
        description="The rules that govern use of SitePilot AI — acceptable use, AI limitations, disclaimers, and liability."
      />

      <Section spacing="lg" aria-labelledby="terms-content-heading">
        <Container size="sm">
          <h2 id="terms-content-heading" className="sr-only">
            Terms and conditions content
          </h2>
          <Text variant="caption" className="mb-8 text-foreground-subtle">
            Last updated: July 13, 2026
          </Text>
          <Prose>
            <p>
              These Terms & Conditions (“Terms”) govern access to and use of {siteConfig.name}
              (“SitePilot”, “we”, “us”) and related websites, APIs, and services. By using the
              service, you agree to these Terms. If you do not agree, do not use SitePilot.
            </p>

            <h2 id="acceptable-use">Acceptable use</h2>
            <p>You agree not to:</p>
            <ul>
              <li>Audit websites you are not authorized to analyze</li>
              <li>Attempt to bypass security, rate limits, or access controls</li>
              <li>Use the service to distribute malware, spam, or unlawful content</li>
              <li>Probe, scrape, or overload SitePilot infrastructure beyond normal use</li>
              <li>Misrepresent AI explanations as independent certifications or warranties</li>
              <li>Reverse engineer the service except where permitted by law</li>
            </ul>

            <h2 id="no-warranties">No warranties</h2>
            <p>
              The service is provided <strong>“as is”</strong> and <strong>“as available”</strong>{" "}
              without warranties of any kind, whether express, implied, or statutory — including
              merchantability, fitness for a particular purpose, and non-infringement. We do not
              warrant that audits will be uninterrupted, error-free, or complete for every site.
            </p>

            <h2 id="ai-limitations">AI limitations</h2>
            <p>
              Optional AI features generate explanations from completed audit artifacts. AI
              output may be incomplete, imprecise, or context-limited. AI does not crawl your
              site independently, does not invent engine checks, and is not a substitute for
              professional legal, security, SEO, or accessibility advice. Always verify critical
              decisions against primary findings and your own expertise.
            </p>

            <h2 id="rate-limits">Rate limits</h2>
            <p>
              We may enforce rate limits, quotas, or fair-use controls on audits, AI generation,
              exports, and share creation to protect service reliability. Exceeding limits may
              result in temporary throttling or refusal of requests.
            </p>

            <h2 id="report-accuracy">Report accuracy disclaimer</h2>
            <p>
              Reports reflect automated observations at the time of the audit under configured
              constraints (crawl depth, timeouts, public accessibility, and similar). Sites
              change; third-party blockers, geo restrictions, and bot defenses can affect
              results. Scores and recommendations are decision-support tools — not guarantees of
              ranking, conversion, compliance, or security posture.
            </p>

            <h2 id="ip">Intellectual property</h2>
            <p>
              SitePilot, including software, branding, documentation, and UI, is owned by
              SitePilot or its licensors. You retain rights to your submitted URLs and to report
              content generated for you, subject to these Terms. You grant us a limited license
              to process submitted URLs and related data solely to provide and improve the
              service.
            </p>

            <h2 id="liability">Limitation of liability</h2>
            <p>
              To the maximum extent permitted by law, SitePilot and its contributors are not
              liable for any indirect, incidental, special, consequential, or punitive damages,
              or for lost profits, revenue, data, or goodwill, arising from use of the service —
              even if advised of the possibility. Our aggregate liability for claims relating to
              the service is limited to the greater of fees you paid us for the service in the
              three months preceding the claim or one hundred U.S. dollars (US$100).
            </p>

            <h2 id="termination">Termination</h2>
            <p>
              We may suspend or terminate access if you violate these Terms, create risk to the
              service or other users, or as required by law. You may stop using SitePilot at any
              time. Provisions that by nature should survive (including disclaimers, IP, and
              liability limits) will survive termination.
            </p>

            <h2 id="changes">Changes to terms</h2>
            <p>
              We may update these Terms from time to time. Continued use after changes become
              effective constitutes acceptance of the revised Terms. The “Last updated” date on
              this page reflects the latest revision.
            </p>

            <h2 id="governing-law">Governing law</h2>
            <p>
              These Terms are governed by the laws of the applicable jurisdiction in which
              SitePilot operates, without regard to conflict-of-law principles.{" "}
              <strong>Governing law and venue details will be finalized in a later legal
              review</strong> — this section is a placeholder for production counsel.
            </p>

            <h2 id="contact">Contact</h2>
            <p>
              Questions about these Terms:{" "}
              <a href={`mailto:${siteConfig.email}`}>{siteConfig.email}</a> or{" "}
              <Link href={ROUTES.contact}>Contact</Link>. Related:{" "}
              <Link href={ROUTES.privacy}>Privacy Policy</Link>.
            </p>
          </Prose>
        </Container>
      </Section>
    </MarketingShell>
  );
}

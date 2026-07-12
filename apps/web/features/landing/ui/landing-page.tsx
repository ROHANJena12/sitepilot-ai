import { MarketingNavbar } from "@/widgets/navbar";
import { LandingHero } from "@/widgets/hero";
import { MarketingFooter } from "@/widgets/footer";

import { TrustedTechnologies } from "./trusted-technologies";
import { LandingFeatures } from "./features-grid";
import { HowItWorks } from "./how-it-works";
import { WhySitePilot } from "./why-sitepilot";
import { ClosingCta } from "./closing-cta";

/**
 * Landing page composition shell for `/`.
 * No API calls or business logic — static marketing experience only.
 */
export function LandingPage() {
  return (
    <>
      <a href="#main-content" className="skip-link">
        Skip to content
      </a>
      <MarketingNavbar />
      <main id="main-content">
        <LandingHero />
        <TrustedTechnologies />
        <LandingFeatures />
        <HowItWorks />
        <WhySitePilot />
        <ClosingCta />
      </main>
      <MarketingFooter />
    </>
  );
}

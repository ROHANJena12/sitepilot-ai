import { TermsPage } from "@/features/marketing";
import { createPageMetadata } from "@/shared/lib/seo";
import { ROUTES } from "@/shared/constants/routes";

export const metadata = createPageMetadata({
  title: "Terms & Conditions",
  description:
    "SitePilot AI terms covering acceptable use, AI limitations, rate limits, report accuracy, liability, and termination.",
  path: ROUTES.terms,
});

/**
 * Route: /terms
 * Thin composition shell — legal content in features/marketing.
 */
export default function Page() {
  return <TermsPage />;
}

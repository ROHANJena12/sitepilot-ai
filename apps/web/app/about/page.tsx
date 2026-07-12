import { AboutPage } from "@/features/marketing";
import { createPageMetadata } from "@/shared/lib/seo";
import { ROUTES } from "@/shared/constants/routes";

export const metadata = createPageMetadata({
  title: "About",
  description:
    "Learn what SitePilot AI is, how the audit pipeline works, why AI explanations are grounded, and where the product is headed.",
  path: ROUTES.about,
});

/**
 * Route: /about
 * Thin composition shell — content lives in features/marketing.
 */
export default function Page() {
  return <AboutPage />;
}

import { LandingPage } from "@/features/landing";
import { siteConfig } from "@/shared/config/site";
import { createPageMetadata } from "@/shared/lib/seo";
import { ROUTES } from "@/shared/constants/routes";

export const metadata = createPageMetadata({
  title: "Website Intelligence Platform",
  description: siteConfig.description,
  path: ROUTES.home,
});

/**
 * Route: /
 * Thin composition shell — landing lives in features/landing + widgets.
 */
export default function Page() {
  return <LandingPage />;
}

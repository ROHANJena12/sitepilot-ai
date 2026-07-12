import { PrivacyPage } from "@/features/marketing";
import { createPageMetadata } from "@/shared/lib/seo";
import { ROUTES } from "@/shared/constants/routes";

export const metadata = createPageMetadata({
  title: "Privacy Policy",
  description:
    "How SitePilot AI collects and protects audit URLs, reports, AI processing context, cookies, and related data.",
  path: ROUTES.privacy,
});

/**
 * Route: /privacy
 * Thin composition shell — legal content in features/marketing.
 */
export default function Page() {
  return <PrivacyPage />;
}

import { ContactPage } from "@/features/marketing";
import { createPageMetadata } from "@/shared/lib/seo";
import { ROUTES } from "@/shared/constants/routes";

export const metadata = createPageMetadata({
  title: "Contact",
  description:
    "Contact the SitePilot AI team by email or LinkedIn. Send a message — form delivery is coming soon.",
  path: ROUTES.contact,
});

/**
 * Route: /contact
 * Thin composition shell — form UI is frontend-only (no API).
 */
export default function Page() {
  return <ContactPage />;
}

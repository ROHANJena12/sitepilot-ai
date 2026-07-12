import { FaqPage } from "@/features/marketing";
import { createPageMetadata } from "@/shared/lib/seo";
import { ROUTES } from "@/shared/constants/routes";

export const metadata = createPageMetadata({
  title: "FAQ",
  description:
    "Frequently asked questions about SitePilot audits, scores, AI explanations, export, sharing, and data storage.",
  path: ROUTES.faq,
});

/**
 * Route: /faq
 * Thin composition shell — FAQ accordion in features/marketing.
 */
export default function Page() {
  return <FaqPage />;
}

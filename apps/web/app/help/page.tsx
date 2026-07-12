import { HelpPage } from "@/features/marketing";
import { createPageMetadata } from "@/shared/lib/seo";
import { ROUTES } from "@/shared/constants/routes";

export const metadata = createPageMetadata({
  title: "Help Center",
  description:
    "Searchable SitePilot help for getting started, audits, scores, AI insights, sharing, export, and troubleshooting.",
  path: ROUTES.help,
});

/**
 * Route: /help
 * Thin composition shell — Help Center in features/marketing.
 */
export default function Page() {
  return <HelpPage />;
}

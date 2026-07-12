import { ReportDemoPlaceholder } from "@/features/report/ui/report-demo-placeholder";
import { createPageMetadata } from "@/shared/lib/seo";
import { ROUTES } from "@/shared/constants/routes";

export const metadata = createPageMetadata({
  title: "Sample report",
  description:
    "Preview how a SitePilot AI website health report is organized before running a live audit.",
  path: ROUTES.reportDemo,
  noIndex: true,
});

/**
 * Route: /report/demo
 * Lightweight sample preview — live reports use /report/[auditId].
 */
export default function Page() {
  return <ReportDemoPlaceholder />;
}

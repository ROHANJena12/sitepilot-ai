import * as React from "react";
import type { Metadata } from "next";

import { AuditInputPage } from "@/features/audit";
import { Spinner } from "@/shared/ui/feedback";

export const metadata: Metadata = {
  title: "Analyze a website",
  description: "Enter a public URL to start a SitePilot AI website analysis.",
};

function AuditFallback() {
  return (
    <div className="flex min-h-[50dvh] items-center justify-center bg-bg">
      <Spinner size="lg" label="Loading audit" />
    </div>
  );
}

/**
 * Route: /audit
 * Thin shell — audit input UI lives in features/audit.
 */
export default function Page() {
  return (
    <React.Suspense fallback={<AuditFallback />}>
      <AuditInputPage />
    </React.Suspense>
  );
}

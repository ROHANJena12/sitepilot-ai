import * as React from "react";
import type { Metadata } from "next";

import { AuditAnalyzingPage } from "@/features/audit";
import { Spinner } from "@/shared/ui/feedback";

export const metadata: Metadata = {
  title: "Analyzing website",
  description: "Live engine pipeline while SitePilot AI analyzes your website.",
};

function AnalyzingFallback() {
  return (
    <div className="flex min-h-[50dvh] items-center justify-center bg-bg">
      <Spinner size="lg" label="Loading analysis" />
    </div>
  );
}

/**
 * Route: /audit/analyzing
 * Starts POST /audits and shows progress until the report is ready.
 */
export default function Page() {
  return (
    <React.Suspense fallback={<AnalyzingFallback />}>
      <AuditAnalyzingPage />
    </React.Suspense>
  );
}

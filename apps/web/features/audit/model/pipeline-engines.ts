/**
 * Live pipeline engine names (matches AuditPipeline order).
 */

export const PIPELINE_ENGINES = [
  { key: "url_validation", label: "URL Validation" },
  { key: "crawler", label: "Website Crawl" },
  { key: "parser", label: "HTML Parsing" },
  { key: "seo", label: "SEO Analysis" },
  { key: "accessibility", label: "Accessibility" },
  { key: "security", label: "Security" },
  { key: "performance", label: "Performance" },
  { key: "business", label: "Business Impact" },
  { key: "health", label: "Health Score" },
  { key: "recommendation", label: "Recommendations" },
] as const;

export type EngineStepStatus = "pending" | "active" | "complete" | "failed";

export function engineIndexFor(current: string | null | undefined): number {
  if (!current) return -1;
  const idx = PIPELINE_ENGINES.findIndex(
    (e) => e.key === current || e.label.toLowerCase() === current.toLowerCase(),
  );
  return idx;
}

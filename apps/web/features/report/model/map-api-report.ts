import type { IssueSeverity } from "@/shared/ui/feedback/issue-severity-badge";
import type { AuditReport, ReportFinding, ReportRecommendation } from "@/shared/types/report";

export type ReportDashboardView = {
  auditId: string;
  websiteUrl: string;
  host: string;
  auditDate: string;
  status: string;
  overallHealth: number;
  summaryText: string;
  summaryBullets: string[];
  scores: Array<{ label: string; value: number; description: string }>;
  issues: Array<{
    id: string;
    resourceId: string | null;
    title: string;
    severity: IssueSeverity;
    category: string;
    description: string;
    businessImpact: string;
    effort: string;
    confidence: number;
    status: string;
  }>;
  recommendations: Array<{
    id: string;
    resourceId: string | null;
    title: string;
    priority: string;
    difficulty: string;
    estimatedImprovement: string;
    expectedImpact: string;
    confidence: number;
    isQuickWin?: boolean;
    description: string;
  }>;
  quickWins: Array<{
    id: string;
    resourceId: string | null;
    title: string;
    priority: string;
    difficulty: string;
    estimatedImprovement: string;
    expectedImpact: string;
    confidence: number;
    isQuickWin?: boolean;
    description: string;
  }>;
  businessImpact: Array<{ domain: string; signal: string; statement: string }>;
  roi: {
    band: string;
    headline: string;
    summary: string;
    items: Array<{ label: string; value: string; tone: "success" | "warning" | "accent" }>;
  };
  charts: {
    healthDistribution: Array<{ name: string; score: number }>;
    issueSeverity: Array<{ name: string; count: number }>;
    performanceBreakdown: Array<{ name: string; value: number }>;
  };
};

function toSeverity(raw: string): IssueSeverity {
  const s = raw.toLowerCase();
  if (s === "critical" || s === "high" || s === "medium" || s === "low") return s;
  return "medium";
}

function formatDate(iso: string | null | undefined): string {
  if (!iso) return "—";
  try {
    return new Date(iso).toLocaleDateString(undefined, {
      year: "numeric",
      month: "long",
      day: "numeric",
    });
  } catch {
    return iso;
  }
}

function mapFinding(f: ReportFinding) {
  return {
    id: f.id,
    resourceId: f.resource_id ?? null,
    title: f.title,
    severity: toSeverity(f.severity),
    category: f.category,
    description: f.description || f.title,
    businessImpact: f.impact || "See technical detail for business context.",
    effort: "—",
    confidence: f.confidence ?? 0,
    status: f.status,
  };
}

function mapRec(r: ReportRecommendation) {
  return {
    id: r.recommendation_id,
    resourceId: r.resource_id ?? null,
    title: r.title,
    priority: r.priority,
    difficulty: r.estimated_effort,
    estimatedImprovement: r.estimated_impact,
    expectedImpact: r.business_reason || r.description,
    confidence: r.confidence ?? 0,
    isQuickWin: Boolean(r.is_quick_win),
    description: r.description,
  };
}

const CATEGORY_META: Record<string, { label: string; description: string }> = {
  seo: { label: "SEO", description: "Metadata & structure" },
  performance: { label: "Performance", description: "Load & vitals signals" },
  security: { label: "Security", description: "Headers & TLS" },
  accessibility: { label: "Accessibility", description: "WCAG-aligned checks" },
  business: { label: "Business Impact", description: "Outcome readiness" },
};

export function mapAuditReportToDashboard(report: AuditReport): ReportDashboardView {
  const host =
    report.overview.website.host ||
    (() => {
      try {
        return new URL(report.overview.website.url).hostname;
      } catch {
        return report.overview.website.url;
      }
    })();

  const scores = (["seo", "performance", "security", "accessibility", "business"] as const).map(
    (key) => {
      const section = report[key];
      const meta = CATEGORY_META[key] ?? { label: key, description: key };
      return {
        label: meta.label,
        value: section?.score ?? report.health.category_scores?.[key] ?? 0,
        description: meta.description,
      };
    },
  );

  const stats = report.statistics as Record<string, number>;
  const issueSeverity = [
    { name: "Critical", count: Number(stats.critical_count ?? 0) },
    { name: "High", count: Number(stats.high_count ?? 0) },
    { name: "Medium", count: Number(stats.medium_count ?? 0) },
    { name: "Low", count: Number(stats.low_count ?? 0) },
  ];

  const summaryBullets = report.summary
    .split(/(?<=\.)\s+/)
    .map((s) => s.trim())
    .filter(Boolean)
    .slice(0, 8);

  const qwCount = report.quick_wins.length;
  const overall = report.health.overall_score ?? report.overview.overall_score ?? 0;

  return {
    auditId: report.audit_id,
    websiteUrl: report.overview.website.url,
    host,
    auditDate: formatDate(report.overview.audit_date || report.generated_at),
    status: report.overview.status || report.status,
    overallHealth: overall,
    summaryText: report.summary,
    summaryBullets: summaryBullets.length ? summaryBullets : [report.summary],
    scores,
    issues: (report.critical_issues.length
      ? report.critical_issues
      : [...report.seo.findings, ...report.accessibility.findings, ...report.security.findings]
          .filter((f) => ["critical", "high"].includes(f.severity.toLowerCase()))
          .slice(0, 12)
    ).map(mapFinding),
    recommendations: report.recommendations.slice(0, 12).map(mapRec),
    quickWins: report.quick_wins.slice(0, 8).map(mapRec),
    businessImpact: report.business_impacts.slice(0, 12).map((f) => ({
      domain: f.category,
      signal: f.severity,
      statement: f.impact || f.description || f.title,
    })),
    roi: {
      band: qwCount >= 5 ? "High" : qwCount >= 2 ? "Medium" : "Emerging",
      headline: `${qwCount} quick win${qwCount === 1 ? "" : "s"} identified`,
      summary:
        "Deterministic priority from the recommendation engine — AI can explain why each matters.",
      items: [
        {
          label: "Overall health",
          value: String(overall),
          tone: overall >= 70 ? "success" : overall >= 40 ? "accent" : "warning",
        },
        {
          label: "Recommendations",
          value: String(report.recommendations.length),
          tone: "accent",
        },
        {
          label: "Quick wins",
          value: String(qwCount),
          tone: qwCount > 0 ? "success" : "warning",
        },
      ],
    },
    charts: {
      healthDistribution: scores.map((s) => ({ name: s.label, score: s.value })),
      issueSeverity,
      performanceBreakdown: Object.entries(report.performance.statistics || {}).map(
        ([name, value]) => ({ name, value: Number(value) }),
      ),
    },
  };
}

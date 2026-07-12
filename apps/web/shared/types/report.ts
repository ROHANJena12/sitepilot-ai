/** Live audit report DTO (matches apps/api AuditReportDTO). */

export type WebsiteMeta = {
  website_id: string;
  url: string;
  canonical_url: string;
  host?: string | null;
  is_https?: boolean | null;
  title?: string | null;
  favicon_url?: string | null;
  language?: string | null;
};

export type ReportFinding = {
  id: string;
  rule_id: string;
  title: string;
  description?: string | null;
  severity: string;
  status: string;
  evidence?: Record<string, unknown>;
  location?: string | null;
  impact?: string | null;
  category: string;
  engine?: string | null;
  confidence?: number | null;
  /** Row UUID for AI endpoints */
  resource_id?: string | null;
};

export type ReportRecommendation = {
  recommendation_id: string;
  title: string;
  description: string;
  priority: string;
  category: string;
  estimated_effort: string;
  estimated_impact: string;
  confidence?: number | null;
  source_finding_ids?: string[];
  related_rules?: string[];
  technical_reason?: string | null;
  business_reason?: string | null;
  is_quick_win?: boolean;
  priority_score?: number | null;
  /** Row UUID for AI endpoints */
  resource_id?: string | null;
};

export type CategorySection = {
  key: string;
  score?: number | null;
  grade?: string | null;
  summary: string;
  statistics?: Record<string, number>;
  findings: ReportFinding[];
  recommendations: ReportRecommendation[];
};

export type HealthSection = {
  overall_score?: number | null;
  grade?: string | null;
  confidence?: number | null;
  category_scores?: Record<string, number>;
  breakdown?: Record<string, unknown>;
  configuration_version?: string | null;
};

export type AuditReport = {
  report_id?: string | null;
  audit_id: string;
  schema_version: string;
  report_version: number;
  report_hash?: string | null;
  generated_at: string;
  status: string;
  summary: string;
  overview: {
    audit_id: string;
    website: WebsiteMeta;
    audit_date?: string | null;
    started_at?: string | null;
    completed_at?: string | null;
    duration_ms?: number | null;
    pipeline_duration_ms?: number | null;
    overall_score?: number | null;
    overall_grade?: string | null;
    status: string;
    summary_counts?: Record<string, number>;
  };
  health: HealthSection;
  seo: CategorySection;
  accessibility: CategorySection;
  security: CategorySection;
  performance: CategorySection;
  business: CategorySection;
  recommendations: ReportRecommendation[];
  quick_wins: ReportRecommendation[];
  critical_issues: ReportFinding[];
  business_impacts: ReportFinding[];
  statistics: Record<string, unknown>;
  engine_summary: Array<{
    engine: string;
    status: string;
    duration_ms?: number | null;
  }>;
  metadata: Record<string, unknown>;
};

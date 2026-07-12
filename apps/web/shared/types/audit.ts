/** Audit run status / poll payload (API snake_case). */

export type AuditStatus =
  | "pending"
  | "running"
  | "complete"
  | "complete_with_warnings"
  | "failed"
  | "cancelled"
  | string;

export type AuditCreateRequest = {
  website_id: string;
};

export type AuditCreateResponse = {
  audit_id: string;
  status: AuditStatus;
  message: string;
};

export type EngineSummaryItem = {
  engine?: string;
  engine_name?: string;
  status: string;
  duration_ms?: number | null;
  started_at?: string | null;
  completed_at?: string | null;
  error_message?: string | null;
};

export type AuditPollResponse = {
  audit_id: string;
  website_id: string;
  url: string;
  canonical_url?: string | null;
  status: AuditStatus;
  progress: number;
  current_engine: string | null;
  health_score?: number | null;
  scores?: Record<string, number> | null;
  category_scores?: Record<string, number> | null;
  engine_summary?: EngineSummaryItem[];
  failure_code?: string | null;
  failure_message?: string | null;
  duration_ms?: number | null;
  started_at?: string | null;
  completed_at?: string | null;
  created_at?: string;
  updated_at?: string;
};

export function isTerminalAuditStatus(status: string): boolean {
  return (
    status === "complete" ||
    status === "complete_with_warnings" ||
    status === "failed" ||
    status === "cancelled"
  );
}

export function isSuccessfulAuditStatus(status: string): boolean {
  return status === "complete" || status === "complete_with_warnings";
}

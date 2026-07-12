/** AI response + job DTOs (snake_case). */

export type AiQuality = {
  grounded?: boolean;
  validation_passed?: boolean;
  cache_hit?: boolean;
  provider?: string;
  model?: string;
  prompt_version?: string;
  builder_version?: number;
  schema_version?: string;
  feature?: string;
};

export type AiResponse<T = Record<string, unknown>> = {
  generation_id: string;
  result: T;
  quality: AiQuality;
  provider_metadata?: Record<string, unknown> | null;
  telemetry?: Record<string, unknown> | null;
  diagnostics?: Record<string, unknown> | null;
  session_id?: string | null;
  generated_at?: string;
};

export type GenerationJobAccepted = {
  job_id: string;
  status: string;
  progress: number;
};

export type GenerationJob = {
  job_id: string;
  status: string;
  progress: number;
  feature?: string;
  entity_id?: string;
  audit_id?: string | null;
  generation_id?: string | null;
  result_url?: string | null;
  worker?: string | null;
  current_phase?: string | null;
  phase_history?: unknown[];
  events?: unknown[];
  summary?: string | null;
  health?: Record<string, unknown> | null;
  failure_category?: string | null;
  error?: string | null;
  provider?: string | null;
  model?: string | null;
  queue_wait_ms?: number | null;
  execution_ms?: number | null;
  total_duration_ms?: number | null;
  latest_version?: number | null;
};

export type GenerationHistoryItem = {
  version: number;
  generation_id?: string;
  created_at?: string;
  provider?: string | null;
  model?: string | null;
  cache_hit?: boolean | null;
};

export type GenerationHistory = {
  feature: string;
  entity_type: string;
  entity_id: string;
  audit_id?: string | null;
  report_hash?: string | null;
  items: GenerationHistoryItem[];
};

export type WebsiteResponse = {
  id: string;
  project_id: string;
  canonical_url: string;
  original_url: string;
  host: string;
  is_https?: boolean | null;
  created_at: string;
  updated_at: string;
};

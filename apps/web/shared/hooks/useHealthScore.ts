"use client";

import { healthService } from "@/shared/services/health.service";
import { useAuditStatus } from "@/shared/hooks/useAudit";

export function useHealthScore(auditId: string | null | undefined) {
  const audit = useAuditStatus(auditId);
  return {
    ...audit,
    overall: audit.data?.health_score ?? null,
    categories: audit.data?.category_scores ?? null,
    fromService: healthService,
  };
}

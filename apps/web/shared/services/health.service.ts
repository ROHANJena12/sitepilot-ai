import { apiGet } from "@/shared/lib/api";
import type { HealthSection } from "@/shared/types/report";
import type { AuditPollResponse } from "@/shared/types/audit";

/** Health is embedded on audit poll / report — thin helper for score reads. */
export const healthService = {
  async fromAudit(auditId: string): Promise<{
    overall: number | null;
    categories: Record<string, number> | null;
  }> {
    const audit = await apiGet<AuditPollResponse>(`/audits/${auditId}`);
    return {
      overall: audit.health_score ?? null,
      categories: audit.category_scores ?? null,
    };
  },

  fromReportHealth(health: HealthSection) {
    return {
      overall: health.overall_score ?? null,
      categories: health.category_scores ?? null,
      grade: health.grade ?? null,
      confidence: health.confidence ?? null,
    };
  },
};

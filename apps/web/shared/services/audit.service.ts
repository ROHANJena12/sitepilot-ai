import { apiGet, apiPost } from "@/shared/lib/api";
import type {
  AuditCreateResponse,
  AuditPollResponse,
} from "@/shared/types/audit";

export const auditService = {
  create(websiteId: string): Promise<AuditCreateResponse> {
    return apiPost<AuditCreateResponse>(
      "/audits",
      { website_id: websiteId },
      { timeout: 30_000 },
    );
  },

  getById(auditId: string): Promise<AuditPollResponse> {
    return apiGet<AuditPollResponse>(`/audits/${auditId}`);
  },
};

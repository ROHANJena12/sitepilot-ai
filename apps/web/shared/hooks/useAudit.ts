"use client";

import { useMutation, useQuery } from "@tanstack/react-query";

import {
  buildAnalyzingHref,
  rememberAuditHandoff,
  validateForAudit,
} from "@/features/audit/lib/begin-audit";
import { adaptivePollIntervalMs } from "@/shared/lib/polling";
import { auditService } from "@/shared/services/audit.service";
import { websiteService } from "@/shared/services/website.service";
import {
  isSuccessfulAuditStatus,
  isTerminalAuditStatus,
} from "@/shared/types/audit";

export function useCreateWebsite() {
  return useMutation({
    mutationFn: (url: string) => websiteService.createFromUrl(url),
  });
}

export function useCreateAudit() {
  return useMutation({
    mutationFn: (websiteId: string) => auditService.create(websiteId),
  });
}

export function useAuditStatus(auditId: string | null | undefined) {
  return useQuery({
    queryKey: ["audit", auditId],
    queryFn: () => auditService.getById(auditId!),
    enabled: Boolean(auditId),
    refetchInterval: (query) => {
      const status = query.state.data?.status;
      const done = Boolean(status && isTerminalAuditStatus(status));
      return adaptivePollIntervalMs(query.state.dataUpdateCount, done);
    },
  });
}

/**
 * Validate URL → create website → create audit (pending) → analyzing href with auditId.
 * Used by the landing hero so Analyze starts the audit immediately.
 */
export function useStartAuditFromUrl() {
  const createWebsite = useCreateWebsite();
  const createAudit = useCreateAudit();

  return useMutation({
    mutationFn: async (rawUrl: string) => {
      const validated = validateForAudit(rawUrl);
      if (!validated.ok) {
        throw new Error(validated.message);
      }

      const website = await createWebsite.mutateAsync(validated.normalized);
      rememberAuditHandoff(website.id, validated.normalized);

      const audit = await createAudit.mutateAsync(website.id);
      const href = buildAnalyzingHref({
        websiteId: website.id,
        url: validated.normalized,
        auditId: audit.audit_id,
      });

      return { website, audit, url: validated.normalized, href };
    },
  });
}

export { isSuccessfulAuditStatus, isTerminalAuditStatus };

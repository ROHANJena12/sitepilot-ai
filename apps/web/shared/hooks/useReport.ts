"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import { reportService } from "@/shared/services/report.service";

export function useAuditReport(auditId: string | null | undefined) {
  return useQuery({
    queryKey: ["report", auditId],
    queryFn: () => reportService.getByAuditId(auditId!),
    enabled: Boolean(auditId),
    staleTime: 60_000,
    retry: (failureCount, error) => {
      const status = (error as { status?: number })?.status;
      if (status === 409 || status === 404) return failureCount < 8;
      return failureCount < 1;
    },
    retryDelay: 800,
  });
}

export function useSharedReport(token: string | null | undefined) {
  return useQuery({
    queryKey: ["shared-report", token],
    queryFn: () => reportService.getSharedByToken(token!),
    enabled: Boolean(token),
    staleTime: 60_000,
    retry: (failureCount, error) => {
      const status = (error as { status?: number })?.status;
      if (status === 410 || status === 404) return false;
      return failureCount < 1;
    },
  });
}

export function useCreateShareLink() {
  return useMutation({
    mutationFn: (auditId: string) => reportService.createShareLink(auditId),
  });
}

export function useRegenerateReport(auditId: string) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: () => reportService.regenerate(auditId),
    onSuccess: (data) => {
      qc.setQueryData(["report", auditId], data);
    },
  });
}

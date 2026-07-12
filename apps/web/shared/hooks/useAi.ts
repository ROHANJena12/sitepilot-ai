"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import { aiService } from "@/shared/services/ai.service";
import type { AiResponse, GenerationJob } from "@/shared/types/ai";

type AiKind =
  | "finding"
  | "recommendation"
  | "quick-win"
  | "executive"
  | "business";

type GenerateArgs = {
  id: string;
  onProgress?: (job: GenerationJob) => void;
};

function queryKey(kind: AiKind, id: string) {
  return ["ai", kind, id] as const;
}

export function useAiJobRunner() {
  return useMutation({
    mutationFn: async ({
      enqueue,
      onProgress,
    }: {
      enqueue: () => Promise<{ job_id: string; status: string; progress: number }>;
      onProgress?: (job: GenerationJob) => void;
    }) => aiService.runJob(enqueue, { onProgress }),
  });
}

export function useFindingExplanation(resourceId: string | null) {
  return useQuery({
    queryKey: queryKey("finding", resourceId ?? ""),
    queryFn: () => aiService.getFindingExplanation(resourceId!),
    enabled: false,
    staleTime: 5 * 60_000,
    retry: 1,
  });
}

export function useGenerateFinding() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async ({ id, onProgress }: GenerateArgs) => {
      try {
        return await aiService.getFindingLatest(id);
      } catch {
        return aiService.runJob(() => aiService.generateFinding(id), { onProgress });
      }
    },
    onSuccess: (data, { id }) => {
      qc.setQueryData(queryKey("finding", id), data);
    },
  });
}

export function useRegenerateFinding() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (resourceId: string) => aiService.regenerateFinding(resourceId),
    onSuccess: (data, resourceId) => {
      qc.setQueryData(queryKey("finding", resourceId), data);
      void qc.invalidateQueries({ queryKey: ["ai", "versions", "finding", resourceId] });
    },
  });
}

export function useGenerateRecommendation() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async ({ id, onProgress }: GenerateArgs) =>
      aiService.runJob(() => aiService.generateRecommendation(id), { onProgress }),
    onSuccess: (data, { id }) => {
      qc.setQueryData(queryKey("recommendation", id), data);
    },
  });
}

export function useGenerateQuickWin() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async ({ id, onProgress }: GenerateArgs) =>
      aiService.runJob(() => aiService.generateQuickWin(id), { onProgress }),
    onSuccess: (data, { id }) => {
      qc.setQueryData(queryKey("quick-win", id), data);
    },
  });
}

export function useGenerateExecutiveSummary() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async ({ id, onProgress }: GenerateArgs) =>
      aiService.runJob(() => aiService.generateExecutiveSummary(id), { onProgress }),
    onSuccess: (data, { id }) => {
      qc.setQueryData(queryKey("executive", id), data);
    },
  });
}

export function useGenerateBusinessSummary() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async ({ id, onProgress }: GenerateArgs) =>
      aiService.runJob(() => aiService.generateBusinessSummary(id), { onProgress }),
    onSuccess: (data, { id }) => {
      qc.setQueryData(queryKey("business", id), data);
    },
  });
}

export function useRegenerateExecutiveSummary() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (auditId: string) => aiService.regenerateExecutiveSummary(auditId),
    onSuccess: (data, auditId) => {
      qc.setQueryData(queryKey("executive", auditId), data);
    },
  });
}

export function useRegenerateBusinessSummary() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (auditId: string) => aiService.regenerateBusinessSummary(auditId),
    onSuccess: (data, auditId) => {
      qc.setQueryData(queryKey("business", auditId), data);
    },
  });
}

export function useAiVersions(kind: "finding" | "recommendation", resourceId: string | null) {
  return useQuery({
    queryKey: ["ai", "versions", kind, resourceId],
    queryFn: () =>
      kind === "finding"
        ? aiService.getFindingVersions(resourceId!)
        : Promise.reject(new Error("unsupported")),
    enabled: Boolean(resourceId) && kind === "finding",
  });
}

export type { AiResponse };

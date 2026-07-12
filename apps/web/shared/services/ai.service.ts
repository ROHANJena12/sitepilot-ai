import { apiGet, apiPost } from "@/shared/lib/api";
import { adaptivePollIntervalMs } from "@/shared/lib/polling";
import { toUserFacingError } from "@/shared/lib/user-facing-error";
import type {
  AiResponse,
  GenerationHistory,
  GenerationJob,
  GenerationJobAccepted,
} from "@/shared/types/ai";

async function pollUntilComplete(
  jobId: string,
  options?: {
    timeoutMs?: number;
    onProgress?: (job: GenerationJob) => void;
  },
): Promise<GenerationJob> {
  const timeoutMs = options?.timeoutMs ?? 180_000;
  const deadline = Date.now() + timeoutMs;
  let attempt = 0;

  while (Date.now() < deadline) {
    const job = await apiGet<GenerationJob>(`/jobs/${jobId}`);
    options?.onProgress?.(job);
    if (
      job.status === "completed" ||
      job.status === "failed" ||
      job.status === "cancelled"
    ) {
      return job;
    }
    attempt += 1;
    const wait = adaptivePollIntervalMs(attempt, false);
    await new Promise((r) => setTimeout(r, wait === false ? 2000 : wait));
  }
  throw new Error(
    toUserFacingError("timed out", "AI generation timed out. Please try again."),
  );
}

export const aiService = {
  getFindingExplanation(findingResourceId: string) {
    return apiGet<AiResponse>(`/findings/${findingResourceId}/ai/explanation`, {
      timeout: 90_000,
    });
  },

  generateFinding(findingResourceId: string) {
    return apiPost<GenerationJobAccepted>(
      `/findings/${findingResourceId}/ai/generate`,
    );
  },

  regenerateFinding(findingResourceId: string) {
    return apiPost<AiResponse>(
      `/findings/${findingResourceId}/ai/regenerate`,
      {},
      { timeout: 90_000 },
    );
  },

  getFindingLatest(findingResourceId: string) {
    return apiGet<AiResponse>(`/findings/${findingResourceId}/ai/latest`);
  },

  getFindingVersions(findingResourceId: string) {
    return apiGet<GenerationHistory>(
      `/findings/${findingResourceId}/ai/versions`,
    );
  },

  getRecommendationExplanation(recResourceId: string) {
    return apiGet<AiResponse>(
      `/recommendations/${recResourceId}/ai/explanation`,
      { timeout: 90_000 },
    );
  },

  generateRecommendation(recResourceId: string) {
    return apiPost<GenerationJobAccepted>(
      `/recommendations/${recResourceId}/ai/generate`,
    );
  },

  regenerateRecommendation(recResourceId: string) {
    return apiPost<AiResponse>(
      `/recommendations/${recResourceId}/ai/regenerate`,
      {},
      { timeout: 90_000 },
    );
  },

  getQuickWin(recResourceId: string) {
    return apiGet<AiResponse>(
      `/recommendations/${recResourceId}/ai/quick-win`,
      { timeout: 90_000 },
    );
  },

  generateQuickWin(recResourceId: string) {
    return apiPost<GenerationJobAccepted>(
      `/recommendations/${recResourceId}/ai/generate-quick-win`,
    );
  },

  regenerateQuickWin(recResourceId: string) {
    return apiPost<AiResponse>(
      `/recommendations/${recResourceId}/ai/regenerate-quick-win`,
      {},
      { timeout: 90_000 },
    );
  },

  getExecutiveSummary(auditId: string) {
    return apiGet<AiResponse>(`/audits/${auditId}/ai/executive-summary`, {
      timeout: 90_000,
    });
  },

  generateExecutiveSummary(auditId: string) {
    return apiPost<GenerationJobAccepted>(
      `/audits/${auditId}/ai/generate-executive-summary`,
    );
  },

  regenerateExecutiveSummary(auditId: string) {
    return apiPost<AiResponse>(
      `/audits/${auditId}/ai/regenerate-executive-summary`,
      {},
      { timeout: 90_000 },
    );
  },

  getBusinessSummary(auditId: string) {
    return apiGet<AiResponse>(`/audits/${auditId}/ai/business-summary`, {
      timeout: 90_000,
    });
  },

  generateBusinessSummary(auditId: string) {
    return apiPost<GenerationJobAccepted>(
      `/audits/${auditId}/ai/generate-business-summary`,
    );
  },

  regenerateBusinessSummary(auditId: string) {
    return apiPost<AiResponse>(
      `/audits/${auditId}/ai/regenerate-business-summary`,
      {},
      { timeout: 90_000 },
    );
  },

  getJob(jobId: string) {
    return apiGet<GenerationJob>(`/jobs/${jobId}`);
  },

  getJobResult(jobId: string) {
    return apiGet<AiResponse>(`/jobs/${jobId}/result`);
  },

  cancelJob(jobId: string, cancelReason = "USER_REQUESTED") {
    return apiPost<GenerationJob>(`/jobs/${jobId}/cancel`, {
      reason: cancelReason,
    });
  },

  /** Async generate → poll → result. */
  async runJob(
    enqueue: () => Promise<GenerationJobAccepted>,
    options?: { onProgress?: (job: GenerationJob) => void },
  ): Promise<AiResponse> {
    const accepted = await enqueue();
    const job = await pollUntilComplete(accepted.job_id, {
      onProgress: options?.onProgress,
    });

    if (job.status !== "completed") {
      throw new Error(
        toUserFacingError(
          job.error || `Job ${job.status}`,
          "AI generation did not complete. You can retry.",
        ),
      );
    }
    return this.getJobResult(accepted.job_id);
  },

  pollUntilComplete,
};

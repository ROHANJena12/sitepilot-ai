import { apiGet, apiPost } from "@/shared/lib/api";
import { axiosClient } from "@/shared/lib/axios";
import { ApiError } from "@/shared/types/api";
import type { AuditReport } from "@/shared/types/report";

export type ReportExportFormat = "pdf" | "json" | "csv";

export type ShareLinkResponse = {
  share_url: string;
  token: string;
  expires_at: string;
  audit_id: string;
};

const EXPORT_FILENAMES: Record<ReportExportFormat, string> = {
  pdf: "audit-report.pdf",
  json: "audit-report.json",
  csv: "audit-report.csv",
};

function filenameFromDisposition(header: string | undefined, fallback: string): string {
  if (!header) return fallback;
  const match = /filename="?([^";]+)"?/i.exec(header);
  return match?.[1]?.trim() || fallback;
}

function triggerBrowserDownload(blob: Blob, filename: string): void {
  const url = URL.createObjectURL(blob);
  const anchor = document.createElement("a");
  anchor.href = url;
  anchor.download = filename;
  anchor.rel = "noopener";
  document.body.appendChild(anchor);
  anchor.click();
  anchor.remove();
  URL.revokeObjectURL(url);
}

export const reportService = {
  getByAuditId(auditId: string): Promise<AuditReport> {
    return apiGet<AuditReport>(`/audits/${auditId}/report`);
  },

  regenerate(auditId: string): Promise<AuditReport> {
    return apiPost<AuditReport>(
      `/audits/${auditId}/report/regenerate`,
      {},
      { timeout: 60_000 },
    );
  },

  createShareLink(auditId: string): Promise<ShareLinkResponse> {
    return apiPost<ShareLinkResponse>(`/audits/${auditId}/share`, {});
  },

  getSharedByToken(token: string): Promise<AuditReport> {
    return apiGet<AuditReport>(`/share/${encodeURIComponent(token)}`);
  },

  /**
   * Download assembled report export (PDF / JSON / CSV).
   * Uses blob response — no modal; triggers an immediate browser download.
   */
  async downloadExport(auditId: string, format: ReportExportFormat): Promise<void> {
    try {
      const response = await axiosClient.get<Blob>(`/audits/${auditId}/export/${format}`, {
        responseType: "blob",
        headers: { Accept: "*/*" },
        timeout: 90_000,
      });
      const fallback = EXPORT_FILENAMES[format];
      const filename = filenameFromDisposition(
        response.headers["content-disposition"] as string | undefined,
        fallback,
      );
      triggerBrowserDownload(response.data, filename);
    } catch (error: unknown) {
      if (
        typeof error === "object" &&
        error !== null &&
        "response" in error &&
        (error as { response?: { data?: Blob; status?: number } }).response?.data instanceof Blob
      ) {
        const res = (error as { response: { data: Blob; status?: number } }).response;
        try {
          const text = await res.data.text();
          const parsed = JSON.parse(text) as {
            error?: { code?: string; message?: string };
            code?: string;
            message?: string;
          };
          const code = parsed.error?.code || parsed.code || "HTTP_ERROR";
          const message =
            parsed.error?.message || parsed.message || "Export request failed";
          throw new ApiError(res.status ?? 500, code, message);
        } catch (inner) {
          if (inner instanceof ApiError) throw inner;
        }
      }
      throw error;
    }
  },
};

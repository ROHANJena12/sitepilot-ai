import type { AxiosRequestConfig } from "axios";

import { axiosClient } from "@/shared/lib/axios";
import { ApiError, type ApiErrorBody } from "@/shared/types/api";

function toApiError(error: unknown): ApiError {
  if (error instanceof ApiError) return error;

  if (typeof error === "object" && error !== null && "isAxiosError" in error) {
    const ax = error as {
      response?: { status?: number; data?: ApiErrorBody | { detail?: unknown } };
      message?: string;
      code?: string;
    };
    const status = ax.response?.status ?? 0;
    const data = ax.response?.data;

    if (data && typeof data === "object" && "error" in data && data.error) {
      const err = (data as ApiErrorBody).error;
      return new ApiError(status, err.code || "HTTP_ERROR", err.message || "Request failed", {
        details: err.details,
        requestId: err.request_id,
      });
    }

    if (data && typeof data === "object" && "detail" in data) {
      const detail = (data as { detail: unknown }).detail;
      if (typeof detail === "object" && detail !== null && "code" in detail) {
        const d = detail as { code: string; message?: string };
        return new ApiError(status, d.code, d.message || "Request failed");
      }
      if (typeof detail === "string") {
        return new ApiError(status, "HTTP_ERROR", detail);
      }
    }

    if (ax.code === "ECONNABORTED") {
      return new ApiError(408, "TIMEOUT", "The request timed out. Please try again.");
    }

    return new ApiError(
      status || 0,
      status === 0 ? "NETWORK_ERROR" : "HTTP_ERROR",
      ax.message || "Request failed",
    );
  }

  if (error instanceof Error) {
    return new ApiError(0, "UNKNOWN", error.message);
  }
  return new ApiError(0, "UNKNOWN", "Unknown error");
}

export async function apiGet<T>(path: string, config?: AxiosRequestConfig): Promise<T> {
  try {
    const res = await axiosClient.get<T>(path, config);
    return res.data;
  } catch (error) {
    throw toApiError(error);
  }
}

export async function apiPost<T>(
  path: string,
  body?: unknown,
  config?: AxiosRequestConfig,
): Promise<T> {
  try {
    const res = await axiosClient.post<T>(path, body, config);
    return res.data;
  } catch (error) {
    throw toApiError(error);
  }
}

export { toApiError };

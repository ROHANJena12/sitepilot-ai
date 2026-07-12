/**
 * Shared API error / envelope types (snake_case JSON from FastAPI).
 */

export type ApiErrorBody = {
  error: {
    code: string;
    message: string;
    details?: Record<string, unknown> | null;
    request_id?: string | null;
    retry_after?: number | null;
  };
};

export class ApiError extends Error {
  readonly status: number;
  readonly code: string;
  readonly details?: Record<string, unknown> | null;
  readonly requestId?: string | null;

  constructor(
    status: number,
    code: string,
    message: string,
    options?: { details?: Record<string, unknown> | null; requestId?: string | null },
  ) {
    super(message);
    this.name = "ApiError";
    this.status = status;
    this.code = code;
    this.details = options?.details;
    this.requestId = options?.requestId;
  }
}

export function isApiError(error: unknown): error is ApiError {
  return error instanceof ApiError;
}

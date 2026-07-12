/**
 * API runtime config — reads public env.
 */

export const apiConfig = {
  baseUrl: process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000/api/v1",
} as const;

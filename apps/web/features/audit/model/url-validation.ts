/**
 * UI-only URL format checks for the audit form.
 * Not domain/engine logic — empty/invalid messaging for the input screen.
 */

export type UrlValidationResult =
  | { ok: true; normalized: string }
  | { ok: false; message: string };

export function validateAuditUrl(raw: string): UrlValidationResult {
  const trimmed = raw.trim();

  if (!trimmed || trimmed === "https://" || trimmed === "http://") {
    return { ok: false, message: "Enter a website URL to analyze." };
  }

  let candidate = trimmed;
  if (!/^https?:\/\//i.test(candidate)) {
    candidate = `https://${candidate}`;
  }

  let parsed: URL;
  try {
    parsed = new URL(candidate);
  } catch {
    return { ok: false, message: "That doesn’t look like a valid URL." };
  }

  if (!["http:", "https:"].includes(parsed.protocol)) {
    return { ok: false, message: "Only http and https URLs are supported." };
  }

  const host = parsed.hostname.toLowerCase();
  if (!host.includes(".") && host !== "localhost") {
    return { ok: false, message: "Include a full domain, like example.com." };
  }

  if (host === "localhost" || host.endsWith(".local") || /^\d+\.\d+\.\d+\.\d+$/.test(host)) {
    return {
      ok: false,
      message: "Public websites only — localhost and private IPs can’t be audited.",
    };
  }

  return { ok: true, normalized: parsed.toString().replace(/\/$/, "") };
}

export const EXAMPLE_URLS = [
  "https://vercel.com",
  "https://linear.app",
  "https://stripe.com",
  "https://example.com",
] as const;

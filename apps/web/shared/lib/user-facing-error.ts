/**
 * Map API / runtime errors to short, actionable copy for the UI.
 * Does not change backend contracts — presentation only.
 */
export function toUserFacingError(
  error: unknown,
  fallback = "Something went wrong. Please try again.",
): string {
  const raw =
    typeof error === "string"
      ? error
      : error && typeof error === "object" && "message" in error
        ? String((error as { message: unknown }).message)
        : "";

  const message = raw.trim();
  if (!message) return fallback;

  const lower = message.toLowerCase();

  if (lower.includes("timeout") || lower.includes("timed out")) {
    return "This is taking longer than expected. Wait a moment and try again.";
  }
  if (lower.includes("network") || lower.includes("failed to fetch")) {
    return "Network issue. Check your connection and try again.";
  }
  if (lower.includes("quota") || lower.includes("rate limit") || lower.includes("429")) {
    return "AI capacity is temporarily limited. Try again in a few minutes.";
  }
  if (lower.includes("share_token_expired") || lower.includes("expired")) {
    if (lower.includes("share") || lower.includes("token") || lower.includes("link")) {
      return "This share link has expired. Ask the owner for a new link.";
    }
  }
  if (lower.includes("share_token_invalid") || lower.includes("tamper")) {
    return "This share link is invalid or no longer available.";
  }
  if (lower.includes("report_not_ready") || lower.includes("not ready")) {
    return "The report is not ready yet. Wait for the audit to finish.";
  }
  if (lower.includes("export")) {
    return "Export failed. Please try again in a moment.";
  }
  if (lower.includes("job ") && (lower.includes("failed") || lower.includes("cancelled"))) {
    return "AI generation did not complete. You can retry.";
  }

  // Hide raw SQLAlchemy / stack-ish fragments
  if (
    lower.includes("traceback") ||
    lower.includes("sqlalchemy") ||
    lower.includes("psycopg") ||
    lower.includes("exception:") ||
    message.length > 220
  ) {
    return fallback;
  }

  return message;
}

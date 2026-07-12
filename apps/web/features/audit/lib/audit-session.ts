/**
 * Client session helpers for audit handoff between /audit and /audit/analyzing.
 */

const PENDING_URL_KEY = "sitepilot:pending-audit-url";
const PENDING_WEBSITE_KEY = "sitepilot:pending-website-id";
const RECENT_KEY = "sitepilot:recent-urls";
const COMPLETED_AUDIT_PREFIX = "sitepilot:completed-audit:";
const INFLIGHT_AUDIT_PREFIX = "sitepilot:inflight-audit:";

/** How long an in-flight lock blocks a duplicate POST after refresh. */
const INFLIGHT_TTL_MS = 3 * 60_000;

export function setPendingAuditUrl(url: string) {
  if (typeof window === "undefined") return;
  window.sessionStorage.setItem(PENDING_URL_KEY, url);
}

export function getPendingAuditUrl(): string | null {
  if (typeof window === "undefined") return null;
  return window.sessionStorage.getItem(PENDING_URL_KEY);
}

export function clearPendingAuditUrl() {
  if (typeof window === "undefined") return;
  window.sessionStorage.removeItem(PENDING_URL_KEY);
}

export function setPendingWebsiteId(id: string) {
  if (typeof window === "undefined") return;
  window.sessionStorage.setItem(PENDING_WEBSITE_KEY, id);
}

export function getPendingWebsiteId(): string | null {
  if (typeof window === "undefined") return null;
  return window.sessionStorage.getItem(PENDING_WEBSITE_KEY);
}

export function clearPendingWebsiteId() {
  if (typeof window === "undefined") return;
  window.sessionStorage.removeItem(PENDING_WEBSITE_KEY);
}

export function setCompletedAuditForWebsite(websiteId: string, auditId: string) {
  if (typeof window === "undefined") return;
  window.sessionStorage.setItem(`${COMPLETED_AUDIT_PREFIX}${websiteId}`, auditId);
}

export function getCompletedAuditForWebsite(websiteId: string): string | null {
  if (typeof window === "undefined") return null;
  return window.sessionStorage.getItem(`${COMPLETED_AUDIT_PREFIX}${websiteId}`);
}

export function markAuditInFlight(websiteId: string) {
  if (typeof window === "undefined") return;
  window.sessionStorage.setItem(
    `${INFLIGHT_AUDIT_PREFIX}${websiteId}`,
    String(Date.now()),
  );
}

export function clearAuditInFlight(websiteId: string) {
  if (typeof window === "undefined") return;
  window.sessionStorage.removeItem(`${INFLIGHT_AUDIT_PREFIX}${websiteId}`);
}

/** True when a recent POST for this website may still be in progress. */
export function isAuditInFlight(websiteId: string): boolean {
  if (typeof window === "undefined") return false;
  const raw = window.sessionStorage.getItem(`${INFLIGHT_AUDIT_PREFIX}${websiteId}`);
  if (!raw) return false;
  const startedAt = Number(raw);
  if (!Number.isFinite(startedAt)) return false;
  if (Date.now() - startedAt > INFLIGHT_TTL_MS) {
    clearAuditInFlight(websiteId);
    return false;
  }
  return true;
}

export type RecentAudit = { url: string; label: string; at: number; when?: string };

export type RecentAuditView = RecentAudit & { when: string };

function formatRelativeTime(at: number): string {
  const deltaSec = Math.max(0, Math.round((Date.now() - at) / 1000));
  if (deltaSec < 45) return "Just now";
  if (deltaSec < 3600) return `${Math.max(1, Math.round(deltaSec / 60))}m ago`;
  if (deltaSec < 86400) return `${Math.max(1, Math.round(deltaSec / 3600))}h ago`;
  return `${Math.max(1, Math.round(deltaSec / 86400))}d ago`;
}

export function pushRecentUrl(url: string) {
  if (typeof window === "undefined") return;
  let host = url;
  try {
    host = new URL(url).hostname;
  } catch {
    /* keep */
  }
  const entry: RecentAudit = {
    url,
    label: host,
    at: Date.now(),
  };
  const prev = getRecentUrlsRaw().filter((r) => r.url !== url);
  const next = [entry, ...prev].slice(0, 8);
  window.localStorage.setItem(RECENT_KEY, JSON.stringify(next));
}

function getRecentUrlsRaw(): RecentAudit[] {
  if (typeof window === "undefined") return [];
  try {
    const raw = window.localStorage.getItem(RECENT_KEY);
    if (!raw) return [];
    const parsed = JSON.parse(raw) as Array<Partial<RecentAudit> & { when?: string }>;
    if (!Array.isArray(parsed)) return [];
    return parsed
      .map((item) => {
        if (!item?.url) return null;
        const at =
          typeof item.at === "number" && Number.isFinite(item.at)
            ? item.at
            : Date.now();
        return {
          url: item.url,
          label: item.label || item.url,
          at,
        } satisfies RecentAudit;
      })
      .filter((item): item is RecentAudit => item !== null);
  } catch {
    return [];
  }
}

export function getRecentUrls(): RecentAuditView[] {
  return getRecentUrlsRaw().map((item) => ({
    ...item,
    when: formatRelativeTime(item.at),
  }));
}

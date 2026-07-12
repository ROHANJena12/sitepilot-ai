/**
 * Shared audit handoff helpers for /audit and landing hero.
 * Keeps validation + analyzing URL construction in one place.
 */

import { ROUTES } from "@/shared/constants/routes";

import {
  pushRecentUrl,
  setPendingAuditUrl,
  setPendingWebsiteId,
} from "./audit-session";
import { validateAuditUrl, type UrlValidationResult } from "../model/url-validation";

export type AnalyzingHandoff = {
  websiteId: string;
  url: string;
  auditId?: string;
};

export function validateForAudit(rawUrl: string): UrlValidationResult {
  return validateAuditUrl(rawUrl);
}

/** Build `/audit/analyzing` query — prefer including auditId when the audit already exists. */
export function buildAnalyzingHref(handoff: AnalyzingHandoff): string {
  const params = new URLSearchParams({
    websiteId: handoff.websiteId,
    url: handoff.url,
  });
  if (handoff.auditId) {
    params.set("auditId", handoff.auditId);
  }
  return `${ROUTES.auditAnalyzing}?${params.toString()}`;
}

/** Persist session keys used by the analyzing page (and recent list). */
export function rememberAuditHandoff(websiteId: string, url: string): void {
  setPendingAuditUrl(url);
  setPendingWebsiteId(websiteId);
  pushRecentUrl(url);
}

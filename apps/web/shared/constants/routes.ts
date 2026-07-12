/**
 * Application route path constants — keep in sync with `app/` segments.
 */
export const ROUTES = {
  home: "/",
  audit: "/audit",
  auditAnalyzing: "/audit/analyzing",
  report: "/report",
  reportDemo: "/report/demo",
  share: "/share",
  dashboard: "/dashboard",
  pricing: "/pricing",
  docs: "/docs",
  help: "/help",
  faq: "/faq",
  contact: "/contact",
  about: "/about",
  privacy: "/privacy",
  terms: "/terms",
} as const;

export type AppRoute = (typeof ROUTES)[keyof typeof ROUTES];

export function reportPath(auditId: string) {
  return `/report/${auditId}`;
}

export function sharePath(token: string) {
  return `/share/${token}`;
}

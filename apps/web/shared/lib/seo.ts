import type { Metadata } from "next";

import { siteConfig } from "@/shared/config/site";

type PageSeoInput = {
  title: string;
  description: string;
  path: string;
  noIndex?: boolean;
};

/**
 * Shared metadata for public marketing / legal pages.
 * Uses the site URL + App Router path for canonical + Open Graph.
 */
export function createPageMetadata({
  title,
  description,
  path,
  noIndex = false,
}: PageSeoInput): Metadata {
  const normalized = path.startsWith("/") ? path : `/${path}`;
  const url = new URL(normalized, siteConfig.url).toString();

  return {
    title,
    description,
    alternates: {
      canonical: url,
    },
    openGraph: {
      type: "website",
      url,
      title: `${title} · ${siteConfig.name}`,
      description,
      siteName: siteConfig.name,
    },
    twitter: {
      card: "summary_large_image",
      title: `${title} · ${siteConfig.name}`,
      description,
    },
    ...(noIndex
      ? { robots: { index: false, follow: false } }
      : { robots: { index: true, follow: true } }),
  };
}

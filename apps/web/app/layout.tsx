import type { Metadata } from "next";
import { GeistSans } from "geist/font/sans";
import { GeistMono } from "geist/font/mono";

import { AppProvider } from "@/shared/providers/AppProvider";

import "@/styles/globals.css";

export const metadata: Metadata = {
  metadataBase: new URL("https://sitepilot.ai"),
  title: {
    default: "SitePilot AI",
    template: "%s · SitePilot AI",
  },
  description: "Your AI-powered Website Intelligence Platform.",
  openGraph: {
    type: "website",
    siteName: "SitePilot AI",
    title: "SitePilot AI",
    description: "Your AI-powered Website Intelligence Platform.",
  },
  twitter: {
    card: "summary_large_image",
    title: "SitePilot AI",
    description: "Your AI-powered Website Intelligence Platform.",
  },
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html
      lang="en"
      className={`${GeistSans.variable} ${GeistMono.variable}`}
      suppressHydrationWarning
    >
      <body className="min-h-dvh font-sans">
        <AppProvider>{children}</AppProvider>
      </body>
    </html>
  );
}

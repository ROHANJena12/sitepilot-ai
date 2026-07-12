"use client";

import * as React from "react";
import { Check, Copy, ExternalLink, Share2 } from "lucide-react";

import { useCreateShareLink } from "@/shared/hooks/useReport";
import { copyTextToClipboard, useToast } from "@/shared/ui/feedback";
import { Button } from "@/shared/ui/buttons";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuTrigger,
} from "@/shared/ui/navigation";

type ReportShareMenuProps = {
  auditId: string;
};

export function ReportShareMenu({ auditId }: ReportShareMenuProps) {
  const createShare = useCreateShareLink();
  const { showToast } = useToast();
  const [copied, setCopied] = React.useState(false);
  const [busy, setBusy] = React.useState(false);
  const [canNativeShare, setCanNativeShare] = React.useState(false);

  React.useEffect(() => {
    setCanNativeShare(
      typeof navigator !== "undefined" && typeof navigator.share === "function",
    );
  }, []);

  const ensureShareUrl = React.useCallback(async (): Promise<string | null> => {
    try {
      const result = await createShare.mutateAsync(auditId);
      return result.share_url;
    } catch (error) {
      const message =
        error instanceof Error ? error.message : "Could not create share link";
      showToast(message, "error");
      return null;
    }
  }, [auditId, createShare, showToast]);

  const handleCopy = React.useCallback(async () => {
    setBusy(true);
    try {
      const url = await ensureShareUrl();
      if (!url) return;
      const ok = await copyTextToClipboard(url);
      if (ok) {
        setCopied(true);
        showToast("Copied", "success");
        window.setTimeout(() => setCopied(false), 2000);
      } else {
        showToast("Could not copy link", "error");
      }
    } finally {
      setBusy(false);
    }
  }, [ensureShareUrl, showToast]);

  const handleOpen = React.useCallback(async () => {
    setBusy(true);
    try {
      const url = await ensureShareUrl();
      if (!url) return;
      window.open(url, "_blank", "noopener,noreferrer");
    } finally {
      setBusy(false);
    }
  }, [ensureShareUrl]);

  const handleNativeShare = React.useCallback(async () => {
    setBusy(true);
    try {
      const url = await ensureShareUrl();
      if (!url) return;
      if (typeof navigator !== "undefined" && typeof navigator.share === "function") {
        try {
          await navigator.share({
            title: "SitePilot audit report",
            text: "View this SitePilot report",
            url,
          });
          return;
        } catch (error) {
          // User cancel → silent; other errors fall back to copy.
          if (error instanceof DOMException && error.name === "AbortError") return;
        }
      }
      const ok = await copyTextToClipboard(url);
      if (ok) {
        setCopied(true);
        showToast("Copied", "success");
        window.setTimeout(() => setCopied(false), 2000);
      }
    } finally {
      setBusy(false);
    }
  }, [ensureShareUrl, showToast]);

  return (
    <DropdownMenu>
      <DropdownMenuTrigger asChild>
        <Button
          type="button"
          variant="secondary"
          disabled={busy || createShare.isPending}
          leftIcon={<Share2 className="h-4 w-4" aria-hidden />}
          aria-label="Share report"
        >
          Share
        </Button>
      </DropdownMenuTrigger>
      <DropdownMenuContent align="start">
        {canNativeShare ? (
          <DropdownMenuItem
            onSelect={(event) => {
              event.preventDefault();
              void handleNativeShare();
            }}
          >
            <Share2 className="h-4 w-4" aria-hidden />
            Share…
          </DropdownMenuItem>
        ) : null}
        <DropdownMenuItem
          onSelect={(event) => {
            event.preventDefault();
            void handleCopy();
          }}
        >
          {copied ? (
            <Check className="h-4 w-4 text-success" aria-hidden />
          ) : (
            <Copy className="h-4 w-4" aria-hidden />
          )}
          {copied ? "Copied" : "Copy Link"}
        </DropdownMenuItem>
        <DropdownMenuItem
          onSelect={(event) => {
            event.preventDefault();
            void handleOpen();
          }}
        >
          <ExternalLink className="h-4 w-4" aria-hidden />
          Open in New Tab
        </DropdownMenuItem>
      </DropdownMenuContent>
    </DropdownMenu>
  );
}

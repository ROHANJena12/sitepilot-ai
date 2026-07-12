"use client";

import * as React from "react";
import { ChevronDown, FileDown } from "lucide-react";

import { reportService, type ReportExportFormat } from "@/shared/services/report.service";
import { toUserFacingError } from "@/shared/lib/user-facing-error";
import { isApiError } from "@/shared/types/api";
import { Button } from "@/shared/ui/buttons";
import { useToast } from "@/shared/ui/feedback";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuTrigger,
} from "@/shared/ui/navigation";

type ReportExportMenuProps = {
  auditId: string;
};

const OPTIONS: { format: ReportExportFormat; label: string }[] = [
  { format: "pdf", label: "Export PDF" },
  { format: "json", label: "Export JSON" },
  { format: "csv", label: "Export CSV" },
];

/**
 * Export dropdown — immediately downloads PDF / JSON / CSV (no modal).
 */
export function ReportExportMenu({ auditId }: ReportExportMenuProps) {
  const { showToast } = useToast();
  const [busy, setBusy] = React.useState(false);

  const onExport = async (format: ReportExportFormat) => {
    if (busy) return;
    setBusy(true);
    try {
      await reportService.downloadExport(auditId, format);
      showToast(`Downloaded ${format.toUpperCase()}`, "success");
    } catch (err) {
      const message = toUserFacingError(
        isApiError(err) ? err.message : err,
        "Export failed. Please try again.",
      );
      showToast(message, "error");
    } finally {
      setBusy(false);
    }
  };

  return (
    <DropdownMenu>
      <DropdownMenuTrigger asChild>
        <Button
          type="button"
          variant="secondary"
          size="sm"
          disabled={busy || !auditId}
          aria-busy={busy}
          leftIcon={<FileDown className="h-3.5 w-3.5" aria-hidden />}
          className="flex-1 sm:flex-none"
        >
          {busy ? "Exporting…" : "Export"}
          <ChevronDown className="ml-1.5 h-3.5 w-3.5 opacity-70" aria-hidden />
        </Button>
      </DropdownMenuTrigger>
      <DropdownMenuContent align="end">
        {OPTIONS.map((option) => (
          <DropdownMenuItem
            key={option.format}
            disabled={busy}
            onSelect={() => {
              void onExport(option.format);
            }}
          >
            {option.label}
          </DropdownMenuItem>
        ))}
      </DropdownMenuContent>
    </DropdownMenu>
  );
}

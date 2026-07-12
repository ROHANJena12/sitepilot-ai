"use client";

import * as React from "react";
import { createPortal } from "react-dom";

import { cn } from "@/shared/lib/utils";

type ToastTone = "success" | "error" | "info";

type ToastState = {
  id: number;
  message: string;
  tone: ToastTone;
} | null;

const ToastContext = React.createContext<{
  showToast: (message: string, tone?: ToastTone) => void;
} | null>(null);

let toastId = 0;

export function ToastProvider({ children }: { children: React.ReactNode }) {
  const [toast, setToast] = React.useState<ToastState>(null);
  const timerRef = React.useRef<ReturnType<typeof setTimeout> | null>(null);

  const showToast = React.useCallback((message: string, tone: ToastTone = "info") => {
    if (timerRef.current) clearTimeout(timerRef.current);
    const id = ++toastId;
    setToast({ id, message, tone });
    timerRef.current = setTimeout(() => {
      setToast((current) => (current?.id === id ? null : current));
    }, 2400);
  }, []);

  React.useEffect(() => {
    return () => {
      if (timerRef.current) clearTimeout(timerRef.current);
    };
  }, []);

  return (
    <ToastContext.Provider value={{ showToast }}>
      {children}
      {toast && typeof document !== "undefined"
        ? createPortal(
            <div
              role="status"
              aria-live={toast.tone === "error" ? "assertive" : "polite"}
              className={cn(
                "fixed bottom-6 left-1/2 z-[100] -translate-x-1/2 rounded-md border px-4 py-2 text-sm shadow-md",
                toast.tone === "success" &&
                  "border-success/40 bg-surface text-foreground",
                toast.tone === "error" && "border-danger/40 bg-surface text-foreground",
                toast.tone === "info" && "border-border bg-surface text-foreground",
              )}
            >
              {toast.message}
            </div>,
            document.body,
          )
        : null}
    </ToastContext.Provider>
  );
}

export function useToast() {
  const ctx = React.useContext(ToastContext);
  if (!ctx) {
    return {
      showToast: (message: string) => {
        if (typeof window !== "undefined") {
          // Fallback when provider is missing (should not happen in app shell).
          window.console.info(message);
        }
      },
    };
  }
  return ctx;
}

export async function copyTextToClipboard(text: string): Promise<boolean> {
  try {
    if (typeof navigator !== "undefined" && navigator.clipboard?.writeText) {
      await navigator.clipboard.writeText(text);
      return true;
    }
  } catch {
    // fall through
  }
  try {
    const el = document.createElement("textarea");
    el.value = text;
    el.setAttribute("readonly", "");
    el.style.position = "fixed";
    el.style.left = "-9999px";
    document.body.appendChild(el);
    el.select();
    const ok = document.execCommand("copy");
    document.body.removeChild(el);
    return ok;
  } catch {
    return false;
  }
}

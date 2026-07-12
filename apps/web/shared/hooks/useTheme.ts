"use client";

import { useTheme as useNextTheme } from "next-themes";

/**
 * Theme hook backed by next-themes.
 * Prefer this over inventing a parallel theme context.
 */
export function useThemeMode() {
  const { theme, resolvedTheme, setTheme, systemTheme } = useNextTheme();
  return { theme, resolvedTheme, setTheme, systemTheme };
}

/** Scaffold-compatible alias */
export function useTheme() {
  return useThemeMode();
}

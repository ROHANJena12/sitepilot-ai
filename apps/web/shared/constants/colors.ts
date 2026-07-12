/**
 * Semantic color token names — map to CSS variables in styles/variables.css.
 * Never hardcode hex in components; use Tailwind semantic classes or these refs.
 */

export const COLORS = {
  bg: "var(--color-bg)",
  surface: "var(--color-surface)",
  border: "var(--color-border)",
  text: "var(--color-text)",
  textMuted: "var(--color-text-muted)",
  accent: "var(--color-accent)",
  success: "var(--color-success)",
  warning: "var(--color-warning)",
  danger: "var(--color-danger)",
  info: "var(--color-info)",
} as const;

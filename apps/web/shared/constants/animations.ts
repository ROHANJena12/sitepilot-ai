/**
 * Motion tokens — aligned with docs/DESIGN_SYSTEM.md §14
 */
export const ANIMATIONS = {
  fast: 120,
  base: 200,
  slow: 320,
  score: 600,
} as const;

/** Shared easing for entrances (calm, Linear-like). */
export const EASE_OUT = [0.22, 1, 0.36, 1] as const;

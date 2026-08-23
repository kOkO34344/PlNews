/** Shared scale helpers. The whole UI reads direction the same way. */

export type Tone = "erosion" | "strengthen" | "neutral";

export function tone(direction: number): Tone {
  if (direction < -0.15) return "erosion";
  if (direction > 0.15) return "strengthen";
  return "neutral";
}

export function toneColor(direction: number): string {
  const t = tone(direction);
  if (t === "erosion") return "var(--erosion)";
  if (t === "strengthen") return "var(--strengthen)";
  return "var(--ink-faint)";
}

/**
 * Label maps used to live here. They moved to lib/i18n.ts when the UI gained Bulgarian —
 * a dimension name is vocabulary, not styling, and having one copy per locale in one
 * place is what stops the two drifting apart.
 */

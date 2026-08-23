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

export const DIRECTION_LABEL: Record<number, string> = {
  [-2]: "severe erosion",
  [-1]: "erosion",
  0: "neutral",
  1: "strengthening",
  2: "significant strengthening",
};

export function directionLabel(direction: number): string {
  return DIRECTION_LABEL[Math.round(direction)] ?? "mixed";
}

/** "rule_of_law" → "rule of law" */
export function humanize(dimension: string): string {
  return dimension.replace(/_/g, " ");
}

export const CATEGORY_LABEL: Record<string, string> = {
  bg_politics: "Bulgarian politics",
  global_politics: "Global politics",
  ai_tech_business: "AI · tech · business",
};

/** Editorial lean, abbreviated for the source strip. */
export const LEAN_LABEL: Record<string, string> = {
  left: "L",
  center_left: "CL",
  center: "C",
  center_right: "CR",
  right: "R",
  state_aligned: "state",
  oligarch_linked: "owner",
  unknown: "?",
};

export const CLAIM_LABEL: Record<string, string> = {
  established: "established",
  reported: "reported",
  contested: "contested",
  speculative: "speculative",
};

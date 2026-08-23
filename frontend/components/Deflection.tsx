"use client";

import { motion, useReducedMotion } from "motion/react";
import { humanize, toneColor } from "@/lib/theme";

/**
 * One democracy reading, drawn as a needle deflecting off the page's centre axis.
 *
 * The mark carries two numbers at once: the bar reaches as far as the assessed
 * direction, but only the confidence fraction of it is solid ink. The hatched
 * remainder is the part of the claim the analysis does not stand behind — so a
 * confident −1 and a shaky −2 are visibly different animals.
 */
export default function Deflection({
  dimension,
  direction,
  confidence,
  delay = 0,
}: {
  dimension: string;
  direction: number;
  confidence: number;
  delay?: number;
}) {
  const reduced = useReducedMotion();
  const color = toneColor(direction);
  const magnitude = Math.min(Math.abs(direction) / 2, 1); // 0…1 of the half-track
  const solid = magnitude * Math.max(Math.min(confidence, 1), 0);
  const left = direction < 0;

  const anchor = left ? { right: "50%" } : { left: "50%" };
  const origin = left ? 1 : 0;

  return (
    <div className="deflection">
      <div className="deflection__meta">
        <span className="deflection__label datum">{humanize(dimension)}</span>
        <span className="deflection__value datum" style={{ color }}>
          {direction > 0 ? `+${direction}` : direction}
          <span className="faint"> · {Math.round(confidence * 100)}% confident</span>
        </span>
      </div>

      <div className="deflection__track" role="img"
           aria-label={`${humanize(dimension)}: ${direction > 0 ? "+" : ""}${direction}, ${Math.round(confidence * 100)} percent confidence`}>
        <span className="deflection__axis" aria-hidden />
        {direction !== 0 && (
          <>
            <motion.span
              className="deflection__bar deflection__bar--tail"
              aria-hidden
              style={{ ...anchor, width: `${magnitude * 50}%`, background: color, originX: origin }}
              initial={reduced ? false : { scaleX: 0 }}
              whileInView={{ scaleX: 1 }}
              viewport={{ once: true, margin: "-40px" }}
              transition={{ duration: 0.55, ease: [0.22, 1, 0.36, 1], delay }}
            />
            <motion.span
              className="deflection__bar deflection__bar--solid"
              aria-hidden
              style={{ ...anchor, width: `${solid * 50}%`, background: color, originX: origin }}
              initial={reduced ? false : { scaleX: 0 }}
              whileInView={{ scaleX: 1 }}
              viewport={{ once: true, margin: "-40px" }}
              transition={{ duration: 0.7, ease: [0.22, 1, 0.36, 1], delay: delay + 0.08 }}
            />
          </>
        )}
      </div>
    </div>
  );
}

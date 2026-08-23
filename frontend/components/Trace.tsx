"use client";

import { motion, useReducedMotion } from "motion/react";
import { useState } from "react";
import { toneColor } from "@/lib/theme";
import { useLocale } from "./LocaleContext";
import type { TrendPoint } from "@/lib/api";

/**
 * The hero: a chart-recorder trace of the daily democracy indicator.
 *
 * It draws itself once on load — left to right, the way the paper actually comes
 * out of the machine — then drops a needle tick from the baseline to each reading.
 * Days are clickable: the trace doubles as the archive.
 */
export default function Trace({
  series,
  activeDate,
  onSelect,
}: {
  series: TrendPoint[];
  activeDate?: string;
  onSelect?: (date: string) => void;
}) {
  const reduced = useReducedMotion();
  const { t } = useLocale();
  const [hover, setHover] = useState<TrendPoint | null>(null);

  if (series.length === 0) return null;

  const W = 1000;
  const H = 104;   // a recorder strip is short and wide; tall empty air reads as a bug
  const PAD = 12;
  const step = series.length > 1 ? (W - PAD * 2) / (series.length - 1) : 0;

  // Scale to the data, not to the theoretical ±1. Real daily indicators sit inside
  // ±0.8, and a fixed scale renders every month as the same flat squiggle. The floor
  // stops a genuinely quiet fortnight from being magnified into drama, and the caption
  // states the scale so two months are still comparable.
  const peak = Math.max(0.4, ...series.map((p) => Math.abs(p.net_direction))) * 1.12;
  const clamp = (v: number) => Math.max(-peak, Math.min(peak, v));
  const x = (i: number) => PAD + i * step;
  const y = (v: number) => H / 2 - (clamp(v) / peak) * (H / 2 - PAD);

  const line = series.map((p, i) => `${i ? "L" : "M"}${x(i).toFixed(1)},${y(p.net_direction).toFixed(1)}`).join(" ");
  const shown = hover ?? series.find((p) => p.date === activeDate) ?? series[series.length - 1];

  return (
    <figure className="trace">
      <svg viewBox={`0 0 ${W} ${H}`} className="trace__svg" preserveAspectRatio="none"
           role="img" aria-label={`Democracy indicator across the last ${series.length} digests`}>
        <line x1="0" y1={H / 2} x2={W} y2={H / 2} className="trace__baseline" />

        {series.map((p, i) => (
          <motion.line
            key={`tick-${p.date}`}
            x1={x(i)} y1={H / 2} x2={x(i)}
            stroke={toneColor(p.net_direction)}
            strokeWidth={Math.max(step * 0.36, 2)}
            opacity={0.3}
            initial={reduced ? false : { y2: H / 2 }}
            animate={{ y2: y(p.net_direction) }}
            transition={{ duration: 0.45, delay: 0.45 + i * 0.014, ease: [0.22, 1, 0.36, 1] }}
          />
        ))}

        <motion.path
          d={line}
          className="trace__line"
          initial={reduced ? false : { pathLength: 0 }}
          animate={{ pathLength: 1 }}
          transition={{ duration: 1.4, ease: [0.22, 1, 0.36, 1] }}
        />

        {series.map((p, i) => (
          <circle
            key={p.date}
            cx={x(i)} cy={y(p.net_direction)} r={p.date === shown.date ? 5 : 3}
            fill={toneColor(p.net_direction)}
            className="trace__dot"
          />
        ))}

        {/* Full-height hit targets: a 3px dot is not a click target. */}
        {series.map((p, i) => (
          <rect
            key={`hit-${p.date}`}
            x={x(i) - step / 2} y={0} width={Math.max(step, 6)} height={H}
            fill="transparent"
            className="trace__hit"
            onMouseEnter={() => setHover(p)}
            onMouseLeave={() => setHover(null)}
            onClick={() => onSelect?.(p.date)}
            role={onSelect ? "button" : undefined}
            tabIndex={onSelect ? 0 : undefined}
            aria-label={`${p.date}: net direction ${p.net_direction.toFixed(2)}`}
            onKeyDown={(e) => {
              if (e.key === "Enter" || e.key === " ") onSelect?.(p.date);
            }}
          />
        ))}
      </svg>

      <figcaption className="trace__caption">
        <span className="eyebrow">
          {t("trace.label", { n: series.length, peak: peak.toFixed(2) })}
        </span>
        <span className="datum">
          {t("trace.caption", {
            date: shown.date,
            net: `${shown.net_direction > 0 ? "+" : ""}${shown.net_direction.toFixed(2)}`,
            relevant: shown.relevant,
          })}
        </span>
      </figcaption>
    </figure>
  );
}

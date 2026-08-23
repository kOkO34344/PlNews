"use client";

import { AnimatePresence, motion, useReducedMotion } from "motion/react";
import { useState } from "react";
import Deflection from "./Deflection";
import { CLAIM_LABEL, LEAN_LABEL, directionLabel, tone, toneColor } from "@/lib/theme";
import type { DigestItem } from "@/lib/api";

export default function StoryCard({
  item,
  index,
  expanded,
  onToggle,
  focused,
}: {
  item: DigestItem;
  index: number;
  expanded: boolean;
  onToggle: () => void;
  focused?: boolean;
}) {
  const reduced = useReducedMotion();
  const a = item.analysis;
  const dem = a.democracy;
  const net = dem.relevant ? dem.net_direction : 0;
  const [copied, setCopied] = useState(false);

  return (
    <motion.article
      className="story card"
      data-focused={focused || undefined}
      initial={reduced ? false : { opacity: 0, y: 14 }}
      whileInView={{ opacity: 1, y: 0 }}
      viewport={{ once: true, margin: "-60px" }}
      transition={{ duration: 0.5, ease: [0.22, 1, 0.36, 1], delay: index * 0.06 }}
      layout
    >
      <div className="story__head">
        <span className="story__rank mono" aria-label={`rank ${item.rank} of three`}>
          {String(item.rank).padStart(2, "0")}
        </span>
        <div className="story__title">
          <h3 className="headline">{a.headline}</h3>
          <p className="lede">{a.what_happened}</p>
        </div>
        {dem.relevant ? (
          <span className="chip" data-tone={tone(net)}>
            {directionLabel(net)}
          </span>
        ) : (
          <span className="chip">no institutional stake</span>
        )}
      </div>

      {dem.relevant && dem.impacts.length > 0 && (
        <div className="story__readings">
          {dem.impacts.map((impact, i) => (
            <Deflection
              key={impact.dimension}
              dimension={impact.dimension}
              direction={impact.direction}
              confidence={impact.confidence}
              delay={i * 0.07}
            />
          ))}
        </div>
      )}

      <div className="story__foot">
        <div className="story__sources">
          {item.refs.slice(0, 5).map((r) => (
            <a key={r.url} href={r.url} target="_blank" rel="noreferrer" className="chip"
               title={`${r.source_name} — ${r.lean.replace(/_/g, " ")}, ${r.reliability} reliability`}>
              {r.source_name}
              <span className="faint">{LEAN_LABEL[r.lean] ?? "?"}</span>
            </a>
          ))}
        </div>
        <button className="story__toggle mono" onClick={onToggle} aria-expanded={expanded}>
          {expanded ? "close" : "read the analysis"}
          <motion.span aria-hidden animate={{ rotate: expanded ? 180 : 0 }} className="story__caret">
            ↓
          </motion.span>
        </button>
      </div>

      <AnimatePresence initial={false}>
        {expanded && (
          <motion.div
            className="story__detail"
            initial={reduced ? false : { height: 0, opacity: 0 }}
            animate={{ height: "auto", opacity: 1 }}
            exit={{ height: 0, opacity: 0 }}
            transition={{ duration: 0.4, ease: [0.22, 1, 0.36, 1] }}
          >
            <div className="story__detail-inner">
              <section>
                <p className="eyebrow">Why it matters</p>
                <p className="lede">{a.why_it_matters}</p>
              </section>

              {dem.relevant && dem.impacts.length > 0 && (
                <section>
                  <p className="eyebrow">Reading, in words</p>
                  <ul className="list">
                    {dem.impacts.map((i) => (
                      <li key={i.dimension}>
                        <span className="datum" style={{ color: toneColor(i.direction) }}>
                          {i.dimension.replace(/_/g, " ")}
                        </span>{" "}
                        {i.rationale}
                      </li>
                    ))}
                  </ul>
                </section>
              )}

              {a.claims.length > 0 && (
                <section>
                  <p className="eyebrow">Claims, sorted by how well they stand up</p>
                  <ul className="claims">
                    {a.claims.map((c) => (
                      <li key={c.text}>
                        <span className="chip" data-claim={c.status}>
                          {CLAIM_LABEL[c.status] ?? c.status}
                        </span>
                        <span>
                          {c.text}
                          {c.evidence && <span className="faint"> — {c.evidence}</span>}
                        </span>
                      </li>
                    ))}
                  </ul>
                </section>
              )}

              <section className="framing">
                <p className="eyebrow">Framing check</p>
                <p className="lede">{a.bias.coverage_spread}</p>
                {a.bias.framing_devices.length > 0 && (
                  <p className="small soft">
                    <strong>Devices.</strong> {a.bias.framing_devices.join("; ")}
                  </p>
                )}
                {a.bias.omitted_context.length > 0 && (
                  <p className="small soft">
                    <strong>Left out.</strong> {a.bias.omitted_context.join("; ")}
                  </p>
                )}
                {a.bias.propaganda_markers.length > 0 && (
                  <p className="small" style={{ color: "var(--erosion)" }}>
                    <strong>Propaganda markers.</strong> {a.bias.propaganda_markers.join("; ")}
                  </p>
                )}
              </section>

              {(a.uncertainty || a.contrarian_read) && (
                <section className="doubt">
                  {a.uncertainty && (
                    <p className="lede">
                      <span className="eyebrow">Not known</span>
                      <br />
                      {a.uncertainty}
                    </p>
                  )}
                  {a.contrarian_read && (
                    <p className="lede">
                      <span className="eyebrow">Strongest counter-reading</span>
                      <br />
                      {a.contrarian_read}
                    </p>
                  )}
                </section>
              )}

              {dem.watch_next.length > 0 && (
                <section>
                  <p className="eyebrow">What would settle it</p>
                  <ul className="list">
                    {dem.watch_next.map((w) => <li key={w}>{w}</li>)}
                  </ul>
                </section>
              )}

              <footer className="story__score">
                <span className="datum">{item.score.explanation}</span>
                <span className="datum">
                  score <strong>{item.score.total.toFixed(3)}</strong>
                </span>
                <button
                  className="chip"
                  onClick={() => {
                    navigator.clipboard?.writeText(`${a.headline}\n\n${a.what_happened}`);
                    setCopied(true);
                    setTimeout(() => setCopied(false), 1600);
                  }}
                >
                  {copied ? "copied" : "copy summary"}
                </button>
              </footer>
            </div>
          </motion.div>
        )}
      </AnimatePresence>
    </motion.article>
  );
}

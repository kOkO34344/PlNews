"use client";

import { AnimatePresence, motion, useReducedMotion } from "motion/react";
import { useState } from "react";
import Deflection from "./Deflection";
import { tone, toneColor } from "@/lib/theme";
import { useLocale } from "./LocaleContext";
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
  const { t, claim, direction: dirLabel, lean, dimension: dimName } = useLocale();
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
        <span className="story__rank mono" aria-label={t("story.rankLabel", { n: item.rank })}>
          {String(item.rank).padStart(2, "0")}
        </span>
        <div className="story__title">
          <h3 className="headline">{a.headline}</h3>
          <p className="lede">{a.what_happened}</p>
        </div>
        {dem.relevant ? (
          <span className="chip" data-tone={tone(net)}>
            {dirLabel(net)}
          </span>
        ) : (
          <span className="chip">{t("story.noStake")}</span>
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
               title={`${r.source_name} — ${r.lean.replace(/_/g, " ")} / ${r.reliability}`}>
              {r.source_name}
              <span className="faint">{lean(r.lean)}</span>
            </a>
          ))}
        </div>
        <button className="story__toggle mono" onClick={onToggle} aria-expanded={expanded}>
          {expanded ? t("story.close") : t("story.read")}
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
                <p className="eyebrow">{t("story.why")}</p>
                <p className="lede">{a.why_it_matters}</p>
              </section>

              {dem.relevant && dem.impacts.length > 0 && (
                <section>
                  <p className="eyebrow">{t("story.inWords")}</p>
                  <ul className="list">
                    {dem.impacts.map((i) => (
                      <li key={i.dimension}>
                        <span className="datum" style={{ color: toneColor(i.direction) }}>
                          {dimName(i.dimension)}
                        </span>{" "}
                        {i.rationale}
                      </li>
                    ))}
                  </ul>
                </section>
              )}

              {a.claims.length > 0 && (
                <section>
                  <p className="eyebrow">{t("story.claims")}</p>
                  <ul className="claims">
                    {a.claims.map((c) => (
                      <li key={c.text}>
                        <span className="chip" data-claim={c.status}>
                          {claim(c.status)}
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
                <p className="eyebrow">{t("story.framing")}</p>
                <p className="lede">{a.bias.coverage_spread}</p>
                {a.bias.framing_devices.length > 0 && (
                  <p className="small soft">
                    <strong>{t("story.devices")}</strong> {a.bias.framing_devices.join("; ")}
                  </p>
                )}
                {a.bias.omitted_context.length > 0 && (
                  <p className="small soft">
                    <strong>{t("story.omitted")}</strong> {a.bias.omitted_context.join("; ")}
                  </p>
                )}
                {a.bias.propaganda_markers.length > 0 && (
                  <p className="small" style={{ color: "var(--erosion)" }}>
                    <strong>{t("story.propaganda")}</strong> {a.bias.propaganda_markers.join("; ")}
                  </p>
                )}
              </section>

              {(a.uncertainty || a.contrarian_read) && (
                <section className="doubt">
                  {a.uncertainty && (
                    <p className="lede">
                      <span className="eyebrow">{t("story.unknown")}</span>
                      <br />
                      {a.uncertainty}
                    </p>
                  )}
                  {a.contrarian_read && (
                    <p className="lede">
                      <span className="eyebrow">{t("story.counter")}</span>
                      <br />
                      {a.contrarian_read}
                    </p>
                  )}
                </section>
              )}

              {dem.watch_next.length > 0 && (
                <section>
                  <p className="eyebrow">{t("story.watch")}</p>
                  <ul className="list">
                    {dem.watch_next.map((w) => <li key={w}>{w}</li>)}
                  </ul>
                </section>
              )}

              <footer className="story__score">
                <span className="datum">{item.score.explanation}</span>
                <span className="datum">
                  {t("story.score")} <strong>{item.score.total.toFixed(3)}</strong>
                </span>
                <button
                  className="chip"
                  onClick={() => {
                    navigator.clipboard?.writeText(`${a.headline}\n\n${a.what_happened}`);
                    setCopied(true);
                    setTimeout(() => setCopied(false), 1600);
                  }}
                >
                  {copied ? t("story.copied") : t("story.copy")}
                </button>
              </footer>
            </div>
          </motion.div>
        )}
      </AnimatePresence>
    </motion.article>
  );
}

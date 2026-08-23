"use client";

import { motion, useReducedMotion } from "motion/react";
import type { DeepDive as DeepDiveType, ArticleRef } from "@/lib/api";
import { useLocale } from "./LocaleContext";

/** The day's one long read. Scenarios are the point, so they get the ink. */
export default function DeepDive({ dd, refs }: { dd: DeepDiveType; refs: ArticleRef[] }) {
  const reduced = useReducedMotion();
  const { t } = useLocale();

  return (
    <motion.section
      className="deep card"
      initial={reduced ? false : { opacity: 0, y: 18 }}
      whileInView={{ opacity: 1, y: 0 }}
      viewport={{ once: true, margin: "-80px" }}
      transition={{ duration: 0.6, ease: [0.22, 1, 0.36, 1] }}
    >
      <p className="eyebrow">{t("deep.eyebrow")}</p>
      <h2 className="display deep__title">{dd.title}</h2>
      <p className="lede deep__summary">{dd.executive_summary}</p>

      <div className="deep__grid">
        <div>
          <p className="eyebrow">{t("deep.background")}</p>
          <p className="lede">{dd.background}</p>
        </div>
        <div>
          <p className="eyebrow">{t("deep.mechanisms")}</p>
          <p className="lede">{dd.mechanisms}</p>
        </div>
        <div>
          <p className="eyebrow">{t("deep.stakes")}</p>
          <p className="lede">{dd.democracy_analysis}</p>
        </div>
        <div>
          <p className="eyebrow">{t("deep.precedent")}</p>
          <p className="lede">{dd.comparative_precedent}</p>
        </div>
      </div>

      {dd.stakeholders.length > 0 && (
        <div className="deep__block">
          <p className="eyebrow">{t("deep.stakeholders")}</p>
          <ul className="list">
            {dd.stakeholders.map((s) => <li key={s}>{s}</li>)}
          </ul>
        </div>
      )}

      <div className="deep__block">
        <p className="eyebrow">{t("deep.scenarios")}</p>
        <div className="scenarios">
          {dd.scenarios.map((s, i) => (
            <motion.div
              key={s.name}
              className="scenario"
              initial={reduced ? false : { opacity: 0, x: -10 }}
              whileInView={{ opacity: 1, x: 0 }}
              viewport={{ once: true }}
              transition={{ duration: 0.45, delay: i * 0.09 }}
            >
              <div className="scenario__head">
                <span className="scenario__name">{s.name}</span>
                <span className="datum">{Math.round(s.probability * 100)}%</span>
              </div>
              <div className="scenario__track">
                <motion.span
                  className="scenario__fill"
                  initial={reduced ? false : { scaleX: 0 }}
                  whileInView={{ scaleX: s.probability }}
                  viewport={{ once: true }}
                  transition={{ duration: 0.8, delay: 0.15 + i * 0.09, ease: [0.22, 1, 0.36, 1] }}
                />
              </div>
              <p className="small">{s.description}</p>
              {s.early_indicators.length > 0 && (
                <p className="datum faint">{t("deep.indicators", { list: s.early_indicators.join(" · ") })}</p>
              )}
            </motion.div>
          ))}
        </div>
      </div>

      <div className="deep__two">
        {dd.what_to_watch.length > 0 && (
          <div>
            <p className="eyebrow">{t("deep.watch")}</p>
            <ul className="list">
              {dd.what_to_watch.map((w) => <li key={w}>{w}</li>)}
            </ul>
          </div>
        )}
        {dd.open_questions.length > 0 && (
          <div>
            <p className="eyebrow">{t("deep.open")}</p>
            <ul className="list">
              {dd.open_questions.map((q) => <li key={q}>{q}</li>)}
            </ul>
          </div>
        )}
      </div>

      <div className="deep__counter">
        <p className="eyebrow">{t("deep.counter")}</p>
        <p className="lede">{dd.counterargument}</p>
      </div>

      <footer className="deep__foot">
        <span className="datum">{t("deep.confidence", { n: Math.round(dd.confidence * 100) })}</span>
        <span className="deep__sources">
          {refs.slice(0, 6).map((r) => (
            <a key={r.url} href={r.url} target="_blank" rel="noreferrer" className="chip">
              {r.source_name}
            </a>
          ))}
        </span>
      </footer>
    </motion.section>
  );
}

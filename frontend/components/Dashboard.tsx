"use client";

import { AnimatePresence, motion, useReducedMotion } from "motion/react";
import { useRouter } from "next/navigation";
import { useCallback, useEffect, useMemo, useState } from "react";
import DeepDive from "./DeepDive";
import StoryCard from "./StoryCard";
import ThemeToggle from "./ThemeToggle";
import Trace from "./Trace";
import { CATEGORY_LABEL, toneColor } from "@/lib/theme";
import type { Category, DailyDigest, TrendPoint } from "@/lib/api";

const ORDER: Category[] = ["bg_politics", "global_politics", "ai_tech_business"];

type Filter = "all" | "erosion" | "strengthening" | "contested";

const FILTERS: { key: Filter; label: string }[] = [
  { key: "all", label: "all nine" },
  { key: "erosion", label: "erosion only" },
  { key: "strengthening", label: "strengthening" },
  { key: "contested", label: "contested facts" },
];

export default function Dashboard({
  digest,
  trend,
  isSample,
}: {
  digest: DailyDigest;
  trend: TrendPoint[];
  isSample: boolean;
}) {
  const router = useRouter();
  const reduced = useReducedMotion();
  const [filter, setFilter] = useState<Filter>("all");
  const [open, setOpen] = useState<string | null>(null);
  const [cursor, setCursor] = useState(0);
  const [keyboard, setKeyboard] = useState(false);

  const visible = useMemo(() => {
    const items = [...digest.items].sort(
      (a, b) => ORDER.indexOf(a.category) - ORDER.indexOf(b.category) || a.rank - b.rank,
    );
    if (filter === "all") return items;
    return items.filter((i) => {
      const d = i.analysis.democracy;
      if (filter === "erosion") return d.relevant && d.net_direction < 0;
      if (filter === "strengthening") return d.relevant && d.net_direction > 0;
      return i.analysis.claims.some((c) => c.status === "contested" || c.status === "speculative");
    });
  }, [digest.items, filter]);

  const keys = useMemo(() => visible.map((i) => i.analysis.cluster_key), [visible]);

  // j / k walk the digest, o opens the one under the cursor. Reading nine stories
  // a morning is a keyboard job.
  const onKey = useCallback(
    (e: KeyboardEvent) => {
      if (e.metaKey || e.ctrlKey || e.altKey) return;
      const target = e.target as HTMLElement | null;
      if (target && ["INPUT", "TEXTAREA"].includes(target.tagName)) return;

      if (e.key === "j" || e.key === "k") {
        e.preventDefault();
        setKeyboard(true);
        setCursor((c) => {
          const next = e.key === "j" ? Math.min(c + 1, keys.length - 1) : Math.max(c - 1, 0);
          document.getElementById(`story-${keys[next]}`)?.scrollIntoView({
            behavior: reduced ? "auto" : "smooth",
            block: "center",
          });
          return next;
        });
      }
      if (e.key === "o" || e.key === "Enter") {
        const key = keys[cursor];
        if (key) setOpen((prev) => (prev === key ? null : key));
      }
      if (e.key === "Escape") setOpen(null);
    },
    [cursor, keys, reduced],
  );

  useEffect(() => {
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [onKey]);

  const net = Number(digest.stats?.net_direction ?? 0);
  const relevant = Number(digest.stats?.democracy_relevant ?? 0);

  return (
    <main className="shell">
      <header className="masthead">
        <div className="masthead__bar">
          <p className="eyebrow">
            3-3-3 · Sofia · {new Date(digest.digest_date).toLocaleDateString("en-GB", {
              weekday: "long", day: "numeric", month: "long", year: "numeric",
            })}
          </p>
          <div className="masthead__tools">
            <span className="datum faint">j / k to move · o to open</span>
            <ThemeToggle />
          </div>
        </div>

        <h1 className="display">
          The institutions moved{" "}
          <span style={{ color: toneColor(net) }}>
            {net > 0 ? "+" : ""}
            {net.toFixed(2)}
          </span>{" "}
          today.
        </h1>

        <p className="lede masthead__note">
          {digest.editorial_note ??
            `Nine stories, ${relevant} of them with something institutional at stake.`}
        </p>

        {isSample && (
          <p className="banner mono">
            Sample data. The API returned no digest — run <code>plnews build</code> to fill this in.
          </p>
        )}
      </header>

      <Trace
        series={trend}
        activeDate={digest.digest_date}
        onSelect={(d) => router.push(`/d/${d}`)}
      />

      <nav className="filters" aria-label="Filter today's stories">
        {FILTERS.map((f) => (
          <button
            key={f.key}
            className="chip"
            aria-pressed={filter === f.key}
            onClick={() => setFilter(f.key)}
          >
            {f.label}
          </button>
        ))}
        <span className="datum faint filters__count">
          {visible.length} of {digest.items.length}
        </span>
      </nav>

      {ORDER.map((cat) => {
        const items = visible.filter((i) => i.category === cat);
        return (
          <section key={cat} className="section">
            <div className="section__head">
              <h2 className="eyebrow section__label">{CATEGORY_LABEL[cat]}</h2>
              <span className="datum faint">
                {items.length} {items.length === 1 ? "reading" : "readings"}
              </span>
            </div>

            <AnimatePresence mode="popLayout">
              {items.length === 0 ? (
                <motion.p
                  key={`${cat}-empty`}
                  className="datum faint section__empty"
                  initial={reduced ? false : { opacity: 0 }}
                  animate={{ opacity: 1 }}
                  exit={{ opacity: 0 }}
                >
                  Nothing here under this filter.
                </motion.p>
              ) : (
                items.map((item, i) => (
                  <div key={item.analysis.cluster_key} id={`story-${item.analysis.cluster_key}`}>
                    <StoryCard
                      item={item}
                      index={i}
                      expanded={open === item.analysis.cluster_key}
                      focused={keyboard && keys[cursor] === item.analysis.cluster_key}
                      onToggle={() =>
                        setOpen((prev) =>
                          prev === item.analysis.cluster_key ? null : item.analysis.cluster_key,
                        )
                      }
                    />
                  </div>
                ))
              )}
            </AnimatePresence>
          </section>
        );
      })}

      {digest.deep_dive && <DeepDive dd={digest.deep_dive} refs={digest.deep_dive_refs} />}

      <footer className="colophon">
        <span className="datum">
          {digest.stats?.fetched ?? 0} articles from {digest.stats?.sources ?? 0} sources →{" "}
          {digest.stats?.clusters ?? 0} stories → 9 selected
        </span>
        <span className="datum faint">
          generated {new Date(digest.generated_at).toISOString().slice(0, 16).replace("T", " ")} UTC
        </span>
      </footer>
    </main>
  );
}

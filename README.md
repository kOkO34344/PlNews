# 3-3-3 Democracy-Aware News Analyst

A daily AI news digest: **3 Bulgarian politics · 3 global politics · 3 AI/tech/business**, each
story analysed for what actually happened, how it was framed, and whether democratic institutions
got stronger or weaker — plus one long-form **deep dive** on the day's highest-stakes story.

Delivered to **Telegram**, archived as **Obsidian** markdown, browsable via a small **Next.js**
dashboard, all served from a **FastAPI** backend.

---

## Why it is built this way

Most news summarisers optimise for compression. This one optimises for **judgement under
uncertainty**, which drives three structural choices:

1. **The LLM output is a contract, not prose.** `StoryAnalysis` and `DeepDive` are Pydantic models
   whose JSON Schema is injected into the prompt and validated on the way back. Fields like
   `uncertainty` and `contrarian_read` are mandatory, so the model cannot quietly skip epistemic
   humility. Extra fields are rejected (`extra="forbid"`).
2. **Democracy analysis is a rubric, not a vibe.** Ten named dimensions (`rule_of_law`,
   `media_freedom`, `electoral_integrity`, …), each scored −2…+2 with a rationale and a confidence.
   Weights live in `app/analysis/democracy.py` where you can see and change them — not buried in a
   prompt. `relevant: false` is an expected, common answer.
3. **Selection is explainable.** Every story carries the arithmetic that put it in the digest:
   `democracy 0.72 · impact 0.60 · novelty 0.80 · credibility 0.85 · fit 0.50 · −0.08 (single source)`.
   If the digest looks wrong, you can see exactly which term did it.

Bias handling: each source carries a declared `lean` and `reliability` (including Bulgaria-specific
`state_aligned` / `oligarch_linked`), passed to the model as a **prior about framing, never as
proof about facts**. Balance is not symmetry — where evidence is one-sided the analysis says so;
where it is genuinely contested it says that instead.

---

## Pipeline

```
                ┌──────────── app/jobs/scheduler.py (cron, 07:00 Europe/Sofia) ───────────┐
                │                                                                          │
  RSS feeds ──▶ ingestion ──▶ analysis ──▶ selection ──▶ deep dive ──▶ digest ──▶ delivery │
                │              │            │             │            │                   │
   sources.py   │  classify    │ analyzer   │ selector    │ deepdive   │ builder           │
   rss.py       │  dedupe      │ (Sonnet)   │ 3-3-3 +     │ (Opus,     │ markdown.py       │
   fetcher.py   │  cluster     │ democracy  │ diversity   │  1×/day)   │ telegram_bot.py   │
                └───────────────────────────── repository.py ─────────────────────────────┘
                                                    │
                                            SQLite / Postgres
                                                    │
                                        FastAPI  ──▶  Next.js dashboard
```

| Phase | Module | What it does |
|---|---|---|
| 1. Ingest | `app/ingestion/` | Poll 34 feeds → drop noise (word list + publisher URL section) → route to one of 3 categories → simhash near-dup removal → TF-IDF + token-containment clustering into *stories* → cross-lingual merge pass → extract article bodies (cached on disk) |
| 2. Analyse | `app/analysis/analyzer.py` | One structured LLM call per candidate story cluster (bounded concurrency, per-cluster failure isolation, token budget) |
| 3. Select | `app/selection/selector.py` | Weighted score + penalties (single-source, one-lean coverage, repeat story, entity crowding) → top 3 per category |
| 4. Deep dive | `app/analysis/deepdive.py` | Highest democratic stakes only; skipped entirely on a low-stakes day rather than filled with filler |
| 5. Render | `app/digest/`, `app/delivery/`, `frontend/` | Obsidian note + entity stubs + MOC; Telegram HTML chunks under the 4096-char cap; the dashboard |

---

## Quickstart

```bash
python -m venv .venv && source .venv/bin/activate
pip install -e ".[dev]"
cp .env.example .env          # add ANTHROPIC_API_KEY, TELEGRAM_BOT_TOKEN

plnews initdb                 # create schema + load the source registry
plnews verify-feeds           # check which RSS URLs are actually alive  ← do this first
plnews ingest --no-full-text  # cluster today's news without spending tokens
plnews build                  # full run: analyse, select, deep dive, store, write markdown
plnews show                   # print the latest digest as markdown
plnews push                   # send it to Telegram

uvicorn app.main:app --reload             # API on :8000, docs at /docs
python -m app.jobs.scheduler              # daily cron
python -m app.delivery.telegram_bot       # bot polling

cd frontend && npm install && npm run dev # dashboard on :3000
```

Or `docker compose up` for db + api + worker + bot.

### Telegram

`/today` compact digest · `/full` with framing checks · `/deep` deep dive · `/bg` `/world` `/tech`
one category · `/trend` democracy indicator sparkline · `/sources` registry ·
`/more <topic>` `/less <topic>` steer future selection · `/run` force a rebuild.

Send `/start` to get your chat id, then put it in `TELEGRAM_ALLOWED_CHAT_IDS` — the bot refuses
everyone else.

---

## Layout

```
app/
  config.py            settings + selection weights
  db.py                engine, session_scope, get_db
  repository.py        every SQL statement in the project
  cli.py               plnews initdb|verify-feeds|ingest|build|show|push
  models/
    schemas.py         Pydantic domain + the LLM output contract
    orm.py             SQLAlchemy tables (JSON payloads + promoted query columns)
  ingestion/
    sources.py         registry: feed, lean, reliability, ownership notes, weight
    rss.py             tolerant feed polling
    classify.py        keyword + source-prior category routing
    dedupe.py          simhash near-dups, TF-IDF/containment clustering, continuity links
    translit.py        BG→EN lexicon + romanisation, so one event in two languages is one story
    fetcher.py         trafilatura body extraction with on-disk cache
    pipeline.py        phase 1 orchestration
  analysis/
    prompts.py         ← all prompts, versioned, schema-injected
    llm.py             Anthropic wrapper: JSON-only, retries, budget, StubClient for tests
    analyzer.py        per-cluster analysis
    democracy.py       dimension weights, scoring, sanity flags
    deepdive.py        daily long-form
  selection/selector.py  the 3-3-3
  digest/
    builder.py         the whole daily run
    markdown.py        Obsidian writer
    templates/digest.md.j2
  delivery/
    formatting.py      Telegram HTML + chunking
    telegram_bot.py    commands, inline feedback, push
  api/routes.py        read API + authenticated /run and /feedback
  jobs/scheduler.py    APScheduler cron
frontend/              Next.js 15 + React 19 dashboard (see below)
tests/                 20 tests, no network, no LLM
```

---

## The dashboard

`cd frontend && npm install && npm run dev`

**Institutional Seismograph.** Democratic erosion is legal, incremental and boring — it does not
look like a coup, it looks like a chart drifting. So the page is a chart-recorder printout rather
than a news site: measurement paper, graphite ink, and a diverging two-pole scale because the data
itself diverges.

The signature is the **deflection**. One continuous axis runs down the page and every democracy
reading is a needle swinging off it — left for erosion, right for strengthening. Each bar carries
two numbers at once: it reaches as far as the assessed direction, but only the confidence fraction
is solid ink, so a confident −1 and a shaky −2 look different at a glance. The same idea at day
scale is the hero: a 30-day trace that draws itself left to right on load, autoscaled to the data
and captioned with its scale, with a needle dropped from the baseline to each reading. Click any
day to open that digest.

- Palette: instrument paper `#e9ede7` / oxidised red `#a8321e` / verdigris `#1f6f5c`, and the same
  instrument at night in dark mode. Three-state theme toggle (auto / paper / night).
- Type: Bricolage Grotesque display, Literata body (it carries Cyrillic — Bulgarian source names
  have to set in the same face), IBM Plex Mono for every number and label.
- Motion: one orchestrated page-load sequence, then scroll-triggered deflections, an animated
  expand for the full analysis, and animated scenario probabilities. `prefers-reduced-motion` turns
  all of it off.
- Interaction: filter to erosion / strengthening / contested-facts with animated re-layout, `j`/`k`
  to walk the digest and `o` to open, and a keyboard cursor that only appears once you use it.
- With the API down or before your first `plnews build`, it renders labelled sample data instead of
  an empty page. Everything in `frontend/lib/sample.ts` is invented and the page says so.

---

## Verified so far

```
$ pytest -q
41 passed

$ plnews verify-feeds
34/34 enabled feeds healthy

$ cd frontend && npm run build
✓ Compiled successfully
```

Smoke-verified end to end without network or LLM: schema creation, source registry sync,
article/cluster upsert, analysis persistence, digest round-trip through the DB, Obsidian note +
entity stubs + MOC generation, and every API endpoint including the auth guard.

Verified against the live web: all 34 enabled feeds return entries, and a full ingestion run pulls
~420 articles down to ~210 relevant ones and 36 story clusters across the three categories. The
dashboard was built, run and reviewed in a browser in both themes and at mobile width.

Not yet exercised: real Anthropic calls and real Telegram delivery — both need your keys. Re-run
`plnews verify-feeds` before each deploy; feeds rot, and the command exits non-zero when an enabled
one breaks, so it belongs in CI.

## Cost

~30–40 clusters/day × ~2.5k in / ~800 out on Sonnet, plus one Opus deep dive
(~15k in / ~4k out). Ballpark **$0.30–0.60/day**. `LLM_DAILY_TOKEN_BUDGET` hard-stops a runaway run;
every call is logged to `llm_calls` with tokens and latency.

## Roadmap

- [ ] Alembic migrations (`alembic init migrations`) — `init_db()` is dev-only
- [ ] Embedding-based clustering behind the existing `EmbeddingBackend` seam
- [ ] Calibration harness: score the deep dive's scenario probabilities against what happened
- [ ] Weekly digest + "what I got wrong last week" retro
- [ ] Per-source drift tracking: has an outlet's framing moved over 6 months?

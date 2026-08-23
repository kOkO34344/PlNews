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
| 1. Ingest | `app/ingestion/` | Poll ~32 feeds → drop noise → route to one of 3 categories → simhash near-dup removal → TF-IDF + token-containment clustering into *stories* → extract article bodies (cached on disk) |
| 2. Analyse | `app/analysis/analyzer.py` | One structured LLM call per candidate story cluster (bounded concurrency, per-cluster failure isolation, token budget) |
| 3. Select | `app/selection/selector.py` | Weighted score + penalties (single-source, one-lean coverage, repeat story, entity crowding) → top 3 per category |
| 4. Deep dive | `app/analysis/deepdive.py` | Highest democratic stakes only; skipped entirely on a low-stakes day rather than filled with filler |
| 5. Render | `app/digest/`, `app/delivery/` | Obsidian note + entity stubs + MOC; Telegram HTML chunks under the 4096-char cap |

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
frontend/              Next.js dashboard (no CSS framework, no chart lib)
tests/                 20 tests, no network, no LLM
```

---

## Verified so far

```
$ pytest -q
20 passed
```

Also smoke-verified end to end without network or LLM: schema creation, source registry sync,
article/cluster upsert, analysis persistence, digest round-trip through the DB, Obsidian note +
entity stubs + MOC generation, and every API endpoint including the auth guard.

Not yet exercised against live services: real RSS endpoints, real Anthropic calls, real Telegram
delivery. **Run `plnews verify-feeds` first** — the feed URLs in `sources.py` are best-effort and
some will have moved.

## Cost

~30–40 clusters/day × ~2.5k in / ~800 out on Sonnet, plus one Opus deep dive
(~15k in / ~4k out). Ballpark **$0.30–0.60/day**. `LLM_DAILY_TOKEN_BUDGET` hard-stops a runaway run;
every call is logged to `llm_calls` with tokens and latency.

## Roadmap

- [ ] Alembic migrations (`alembic init migrations`) — `init_db()` is dev-only
- [ ] Embedding-based clustering behind the existing `EmbeddingBackend` seam
- [ ] Cross-lingual clustering so a BG and an EN story about the same event merge
- [ ] Calibration harness: score the deep dive's scenario probabilities against what happened
- [ ] Weekly digest + "what I got wrong last week" retro
- [ ] Per-source drift tracking: has an outlet's framing moved over 6 months?

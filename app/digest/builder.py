"""The daily run, end to end.

    ingest → analyse → select 3-3-3 → deep dive → editorial note → persist → render

Every phase is separately callable so you can re-run just the parts you are working
on (see `app/cli.py`: `plnews ingest`, `plnews analyse`, `plnews build`).
"""
from __future__ import annotations

from datetime import date, datetime, timezone

import structlog
from sqlalchemy.orm import Session

from app.analysis.analyzer import AnalysisOutcome, analyze_all
from app.analysis.deepdive import generate_deep_dive, pick_deep_dive
from app.analysis.democracy import summarize_day
from app.analysis.llm import LLMClient, get_llm_client
from app.analysis.prompts import PROMPT_VERSION, SYSTEM_EDITORIAL_NOTE
from app.config import settings
from app.digest.markdown import write_obsidian_note
from app.ingestion.pipeline import run_ingestion
from app.models.schemas import DailyDigest, DigestItem
from app.selection.selector import select_333
from app import repository as repo

log = structlog.get_logger(__name__)


async def build_daily_digest(session: Session, client: LLMClient | None = None, *,
                             target_date: date | None = None, dry_run: bool = False,
                             write_markdown: bool = True) -> DailyDigest:
    client = client or get_llm_client()
    target_date = target_date or datetime.now(tz=settings.tz).date()
    log.info("digest.start", date=target_date.isoformat())

    # --- 1. ingest ------------------------------------------------------- #
    ingest = await run_ingestion(session)
    session.flush()

    # --- 2. analyse ------------------------------------------------------ #
    outcomes = await analyze_all(client, ingest.all_clusters, ingest.bodies)
    cluster_ids = _persist_analyses(session, outcomes)

    # --- 3. select ------------------------------------------------------- #
    interests = repo.interest_weights(session)
    repeated = _yesterdays_keys(session, target_date)
    items = select_333(outcomes, interests=interests, repeated_keys=repeated)

    # --- 4. deep dive ---------------------------------------------------- #
    deep_dive = None
    deep_dive_refs = []
    chosen = pick_deep_dive(items)
    if chosen and not dry_run:
        cluster = next(o.cluster for o in outcomes if o.cluster.key == chosen.analysis.cluster_key)
        history = repo.cluster_history(session, cluster.key)
        deep_dive = await generate_deep_dive(client, chosen, cluster, ingest.bodies, history)
        deep_dive_refs = cluster.articles

    # --- 5. editorial note ----------------------------------------------- #
    note = None if dry_run else await _editorial_note(client, items)

    digest = DailyDigest(
        digest_date=target_date,
        generated_at=datetime.now(tz=timezone.utc),
        items=items,
        deep_dive=deep_dive,
        deep_dive_refs=deep_dive_refs,
        editorial_note=note,
        stats={
            **ingest.stats,
            **summarize_day([i.analysis for i in items]),
            "llm_tokens_in": getattr(client, "usage", None).tokens_in if hasattr(client, "usage") else 0,
            "llm_tokens_out": getattr(client, "usage", None).tokens_out if hasattr(client, "usage") else 0,
        },
    )

    # --- 6. persist + render --------------------------------------------- #
    if not dry_run:
        md_path = write_obsidian_note(digest) if write_markdown else None
        repo.save_digest(session, digest, cluster_ids, markdown_path=str(md_path) if md_path else None)
        session.commit()

    log.info("digest.done", date=target_date.isoformat(), items=len(items),
             deep_dive=bool(deep_dive), **ingest.stats)
    return digest


def _persist_analyses(session: Session, outcomes: list[AnalysisOutcome]) -> dict[str, int]:
    """Returns {cluster_key: cluster_id}."""
    from sqlalchemy import select

    from app.models.orm import Cluster

    ids: dict[str, int] = {}
    for o in outcomes:
        row = session.scalar(select(Cluster).where(Cluster.key == o.cluster.key))
        if row is None:
            continue
        ids[o.cluster.key] = row.id
        if o.analysis is not None:
            repo.save_analysis(session, row.id, o.analysis, model=o.model,
                               prompt_version=PROMPT_VERSION, tokens_in=o.tokens_in,
                               tokens_out=o.tokens_out)
            repo.log_llm_call(session, purpose="analysis", model=o.model,
                              prompt_version=PROMPT_VERSION, tokens_in=o.tokens_in,
                              tokens_out=o.tokens_out, latency_ms=0, ok=True)
    session.flush()
    return ids


def _yesterdays_keys(session: Session, target_date: date) -> set[str]:
    from datetime import timedelta

    prev = repo.get_digest(session, target_date - timedelta(days=1))
    return {i.analysis.cluster_key for i in prev.items} if prev else set()


async def _editorial_note(client: LLMClient, items: list[DigestItem]) -> str | None:
    if not items:
        return None
    from pydantic import BaseModel

    class Note(BaseModel):
        note: str

    lines = [f"- [{i.category.value}] {i.analysis.headline}" for i in items]
    try:
        res = await client.complete_json(
            system=SYSTEM_EDITORIAL_NOTE, user="\n".join(lines), schema=Note,
            model=settings.llm_model_analysis, max_tokens=400, temperature=0.4,
            purpose="editorial_note",
        )
        return res.data.note
    except Exception as exc:
        log.warning("digest.editorial_note_failed", error=str(exc)[:200])
        return None

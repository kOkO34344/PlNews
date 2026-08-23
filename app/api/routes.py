"""Public read API + a small authenticated control surface."""
from __future__ import annotations

import asyncio
from datetime import date

from fastapi import APIRouter, BackgroundTasks, Depends, Header, HTTPException, Query
from sqlalchemy import desc, select
from sqlalchemy.orm import Session

from app import repository as repo
from app.config import settings
from app.db import get_db, session_scope
from app.models.orm import Analysis, Cluster, Digest, Source
from app.models.schemas import Category, DailyDigest

router = APIRouter()


def require_key(x_api_key: str = Header(default="")) -> None:
    if x_api_key != settings.api_key:
        raise HTTPException(status_code=401, detail="invalid API key")


# ------------------------------------------------------------------ digests --
@router.get("/digests", summary="List available digest dates")
def list_digests(limit: int = Query(30, le=180), db: Session = Depends(get_db)) -> dict:
    return {"dates": [d.isoformat() for d in repo.list_digest_dates(db, limit)]}


@router.get("/digests/latest", response_model=DailyDigest)
def get_latest(db: Session = Depends(get_db)) -> DailyDigest:
    digest = repo.latest_digest(db)
    if digest is None:
        raise HTTPException(404, "no digest generated yet")
    return digest


@router.get("/digests/{digest_date}", response_model=DailyDigest)
def get_by_date(digest_date: date, db: Session = Depends(get_db)) -> DailyDigest:
    digest = repo.get_digest(db, digest_date)
    if digest is None:
        raise HTTPException(404, f"no digest for {digest_date}")
    return digest


@router.get("/digests/{digest_date}/markdown", summary="Obsidian-flavoured markdown")
def get_markdown(digest_date: date, db: Session = Depends(get_db)) -> dict:
    from app.digest.markdown import render_digest_markdown

    digest = repo.get_digest(db, digest_date)
    if digest is None:
        raise HTTPException(404, f"no digest for {digest_date}")
    return {"date": digest_date.isoformat(), "markdown": render_digest_markdown(digest)}


# ----------------------------------------------------------------- analysis --
@router.get("/stories", summary="Analysed story clusters (whether or not they were selected)")
def list_stories(category: Category | None = None, limit: int = Query(50, le=200),
                 db: Session = Depends(get_db)) -> dict:
    stmt = select(Cluster, Analysis).join(Analysis, Analysis.cluster_id == Cluster.id)
    if category:
        stmt = stmt.where(Cluster.category == category.value)
    rows = db.execute(stmt.order_by(desc(Analysis.created_at)).limit(limit)).all()
    return {
        "stories": [
            {
                "key": c.key, "category": c.category, "headline": a.payload.get("headline", c.headline),
                "sources": c.source_count, "democracy_significance": a.democracy_significance,
                "democracy_net": a.democracy_net, "novelty": a.novelty, "credibility": a.credibility,
                "analysis": a.payload,
            }
            for c, a in rows
        ]
    }


@router.get("/democracy/trend", summary="Daily democracy indicator series for charting")
def democracy_trend(days: int = Query(60, le=365), db: Session = Depends(get_db)) -> dict:
    rows = db.scalars(select(Digest).order_by(desc(Digest.digest_date)).limit(days)).all()
    return {
        "series": [
            {
                "date": r.digest_date.isoformat(),
                "net_direction": (r.payload.get("stats") or {}).get("net_direction", 0),
                "relevant": (r.payload.get("stats") or {}).get("democracy_relevant", 0),
                "erosion": (r.payload.get("stats") or {}).get("erosion_stories", 0),
                "strengthening": (r.payload.get("stats") or {}).get("strengthening_stories", 0),
            }
            for r in reversed(rows)
        ]
    }


@router.get("/sources", summary="Source registry with lean/reliability metadata")
def list_sources(db: Session = Depends(get_db)) -> dict:
    rows = db.scalars(select(Source).order_by(Source.name)).all()
    return {
        "sources": [
            {"slug": s.slug, "name": s.name, "lang": s.lang, "country": s.country,
             "categories": s.categories, "lean": s.lean, "reliability": s.reliability,
             "ownership_note": s.ownership_note, "enabled": s.enabled,
             "last_fetched_at": s.last_fetched_at, "last_error": s.last_error}
            for s in rows
        ]
    }


# ----------------------------------------------------------------- feedback --
@router.post("/feedback", dependencies=[Depends(require_key)])
def post_feedback(signal: str, tag: str | None = None, cluster_key: str | None = None,
                  note: str | None = None, db: Session = Depends(get_db)) -> dict:
    if signal not in {"more", "less", "deep_dive", "irrelevant"}:
        raise HTTPException(400, "signal must be one of: more, less, deep_dive, irrelevant")
    cluster_id = None
    if cluster_key:
        c = db.scalar(select(Cluster).where(Cluster.key == cluster_key))
        cluster_id = c.id if c else None
    fb = repo.add_feedback(db, signal=signal, tag=tag, cluster_id=cluster_id, note=note,
                           channel="api")
    db.commit()
    return {"ok": True, "id": fb.id}


# ------------------------------------------------------------------- admin --
@router.post("/run", dependencies=[Depends(require_key)], summary="Trigger a digest build now")
def trigger_run(background: BackgroundTasks, dry_run: bool = False) -> dict:
    background.add_task(_run_build, dry_run)
    return {"ok": True, "status": "started"}


def _run_build(dry_run: bool) -> None:
    from app.digest.builder import build_daily_digest

    async def _go() -> None:
        with session_scope() as db:
            await build_daily_digest(db, dry_run=dry_run)

    asyncio.run(_go())

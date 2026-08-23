"""Storage layer. All SQL lives here; the pipeline stays persistence-agnostic."""
from __future__ import annotations

from datetime import date, datetime, timedelta, timezone

from sqlalchemy import desc, select
from sqlalchemy.orm import Session

from app.ingestion.dedupe import simhash
from app.ingestion.fetcher import url_hash
from app.models.orm import (
    Analysis, Article, Cluster, DeepDiveRow, Digest, DigestItemRow, Feedback, LLMCall, Source,
)
from app.models.schemas import (
    ArticleIn, ArticleRef, Category, DailyDigest, DeepDive, StoryAnalysis, StoryClusterIn,
)


# ---------------------------------------------------------------- articles --
def upsert_articles(session: Session, articles: list[ArticleIn]) -> dict[str, int]:
    """Insert new articles, skip known URLs. Returns {url: article_id}."""
    sources = {s.slug: s.id for s in session.scalars(select(Source)).all()}
    out: dict[str, int] = {}
    for a in articles:
        source_id = sources.get(a.source_slug)
        if source_id is None:
            continue
        h = url_hash(a.url)
        row = session.scalar(select(Article).where(Article.url_hash == h))
        if row is None:
            row = Article(
                source_id=source_id, url_hash=h, url=a.url, title=a.title, summary=a.summary,
                body=a.body, author=a.author, lang=a.lang, published_at=a.published_at,
                simhash=f"{simhash(a.title + ' ' + (a.summary or '')):016x}",
            )
            session.add(row)
            session.flush()
        elif a.body and not row.body:
            row.body = a.body
        out[a.url] = row.id
    return out


def recent_articles(session: Session, hours: int = 30) -> list[Article]:
    cutoff = datetime.now(tz=timezone.utc) - timedelta(hours=hours)
    return list(session.scalars(
        select(Article).where(Article.fetched_at >= cutoff).order_by(desc(Article.published_at))
    ).all())


# ---------------------------------------------------------------- clusters --
def upsert_cluster(session: Session, cluster: StoryClusterIn, article_ids: dict[str, int],
                   parent_key: str | None = None) -> Cluster:
    row = session.scalar(select(Cluster).where(Cluster.key == cluster.key))
    if row is None:
        row = Cluster(key=cluster.key, category=cluster.category.value, headline=cluster.headline,
                      first_seen=cluster.first_seen)
        session.add(row)
        session.flush()
    row.headline = cluster.headline
    row.last_seen = cluster.last_seen
    row.article_count = len(cluster.articles)
    row.source_count = cluster.source_count
    row.parent_key = parent_key or row.parent_key

    for ref in cluster.articles:
        aid = ref.id or article_ids.get(ref.url)
        if aid:
            art = session.get(Article, aid)
            if art is not None:
                art.cluster_id = row.id
    session.flush()
    return row


def clusters_for_day(session: Session, category: Category, since_hours: int = 30) -> list[Cluster]:
    cutoff = datetime.now(tz=timezone.utc) - timedelta(hours=since_hours)
    return list(session.scalars(
        select(Cluster).where(Cluster.category == category.value, Cluster.last_seen >= cutoff)
    ).all())


def previous_cluster_keys(session: Session, days: int = 3) -> list[tuple[str, str]]:
    cutoff = datetime.now(tz=timezone.utc) - timedelta(days=days)
    rows = session.scalars(select(Cluster).where(Cluster.last_seen >= cutoff)).all()
    return [(c.key, c.headline) for c in rows]


def cluster_history(session: Session, key: str, limit: int = 7) -> list[dict]:
    """Prior analyses of this running story, newest first — context for the deep dive."""
    out: list[dict] = []
    seen: set[str] = set()
    current = session.scalar(select(Cluster).where(Cluster.key == key))
    while current is not None and current.key not in seen and len(out) < limit:
        seen.add(current.key)
        if current.analysis:
            payload = current.analysis.payload
            out.append({
                "date": current.last_seen.date().isoformat() if current.last_seen else None,
                "headline": payload.get("headline", current.headline),
                "what_happened": payload.get("what_happened", ""),
            })
        if not current.parent_key:
            break
        current = session.scalar(select(Cluster).where(Cluster.key == current.parent_key))
    return out[1:] if out else []


# ---------------------------------------------------------------- analysis --
def save_analysis(session: Session, cluster_id: int, analysis: StoryAnalysis, model: str,
                  prompt_version: str, tokens_in: int = 0, tokens_out: int = 0) -> Analysis:
    row = session.scalar(select(Analysis).where(Analysis.cluster_id == cluster_id))
    if row is None:
        row = Analysis(cluster_id=cluster_id)
        session.add(row)
    row.model = model
    row.prompt_version = prompt_version
    row.payload = analysis.model_dump(mode="json")
    row.democracy_significance = analysis.democracy.significance if analysis.democracy.relevant else 0.0
    row.democracy_net = analysis.democracy.net_direction
    row.impact_scope = analysis.impact_scope
    row.novelty = analysis.novelty
    row.credibility = analysis.credibility
    row.tokens_in, row.tokens_out = tokens_in, tokens_out
    session.flush()
    return row


def get_analysis(session: Session, cluster_id: int) -> StoryAnalysis | None:
    row = session.scalar(select(Analysis).where(Analysis.cluster_id == cluster_id))
    return StoryAnalysis.model_validate(row.payload) if row else None


def refs_for_cluster(session: Session, cluster_id: int) -> list[ArticleRef]:
    arts = session.scalars(select(Article).where(Article.cluster_id == cluster_id)).all()
    refs: list[ArticleRef] = []
    for a in arts:
        s = session.get(Source, a.source_id)
        refs.append(ArticleRef(
            id=a.id, source_slug=s.slug if s else "?", source_name=s.name if s else "?",
            lean=s.lean if s else "unknown", reliability=s.reliability if s else "medium",  # type: ignore[arg-type]
            title=a.title, url=a.url, published_at=a.published_at,
        ))
    return refs


# ------------------------------------------------------------------ digest --
def save_digest(session: Session, digest: DailyDigest, cluster_ids: dict[str, int],
                markdown_path: str | None = None) -> Digest:
    payload = digest.model_dump(mode="json")
    row = session.scalar(select(Digest).where(Digest.digest_date == digest.digest_date))
    if row is None:
        # payload is NOT NULL: populate before the flush that assigns the id.
        row = Digest(digest_date=digest.digest_date, payload=payload)
        session.add(row)
        session.flush()
    row.generated_at = digest.generated_at
    row.payload = payload
    row.editorial_note = digest.editorial_note
    if markdown_path:
        row.markdown_path = markdown_path

    for old in list(row.items):
        session.delete(old)
    session.flush()

    for item in digest.items:
        cid = cluster_ids.get(item.analysis.cluster_key)
        if cid is None:
            continue
        session.add(DigestItemRow(
            digest_id=row.id, cluster_id=cid, category=item.category.value, rank=item.rank,
            score=item.score.total, score_breakdown=item.score.model_dump(mode="json"),
        ))

    if digest.deep_dive:
        dd_cluster = cluster_ids.get(digest.deep_dive.cluster_key)
        existing = session.scalar(select(DeepDiveRow).where(DeepDiveRow.digest_id == row.id))
        if existing is None and dd_cluster:
            session.add(DeepDiveRow(digest_id=row.id, cluster_id=dd_cluster, model="",
                                    payload=digest.deep_dive.model_dump(mode="json")))
        elif existing is not None:
            existing.payload = digest.deep_dive.model_dump(mode="json")
    session.flush()
    return row


def get_digest(session: Session, d: date) -> DailyDigest | None:
    row = session.scalar(select(Digest).where(Digest.digest_date == d))
    return DailyDigest.model_validate(row.payload) if row else None


def latest_digest(session: Session) -> DailyDigest | None:
    row = session.scalars(select(Digest).order_by(desc(Digest.digest_date)).limit(1)).first()
    return DailyDigest.model_validate(row.payload) if row else None


def list_digest_dates(session: Session, limit: int = 30) -> list[date]:
    rows = session.scalars(select(Digest.digest_date).order_by(desc(Digest.digest_date)).limit(limit)).all()
    return list(rows)


# ---------------------------------------------------------------- feedback --
def add_feedback(session: Session, *, signal: str, cluster_id: int | None = None,
                 tag: str | None = None, note: str | None = None, channel: str = "telegram",
                 digest_date: date | None = None) -> Feedback:
    fb = Feedback(signal=signal, cluster_id=cluster_id, tag=tag, note=note, channel=channel,
                  digest_date=digest_date)
    session.add(fb)
    session.flush()
    return fb


def interest_weights(session: Session, days: int = 60) -> dict[str, float]:
    """Aggregate feedback into per-tag weights used by the `personal` selection term."""
    cutoff = datetime.now(tz=timezone.utc) - timedelta(days=days)
    rows = session.scalars(select(Feedback).where(Feedback.created_at >= cutoff)).all()
    weights: dict[str, float] = {}
    for fb in rows:
        if not fb.tag:
            continue
        delta = {"more": 0.15, "deep_dive": 0.2, "less": -0.15, "irrelevant": -0.3}.get(fb.signal, 0.0)
        weights[fb.tag] = max(-1.0, min(1.0, weights.get(fb.tag, 0.0) + delta))
    return weights


def log_llm_call(session: Session, *, purpose: str, model: str, prompt_version: str, tokens_in: int,
                 tokens_out: int, latency_ms: int, ok: bool = True, error: str | None = None) -> None:
    session.add(LLMCall(purpose=purpose, model=model, prompt_version=prompt_version,
                        tokens_in=tokens_in, tokens_out=tokens_out, latency_ms=latency_ms,
                        ok=ok, error=error))

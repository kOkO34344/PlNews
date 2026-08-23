"""RSS/Atom polling. One coroutine per feed, bounded concurrency, tolerant parsing."""
from __future__ import annotations

import asyncio
from datetime import datetime, timedelta, timezone

import feedparser
import httpx
import structlog

from app.config import settings
from app.models.schemas import ArticleIn, SourceSpec

log = structlog.get_logger(__name__)


def _parse_dt(entry) -> datetime | None:
    for key in ("published_parsed", "updated_parsed"):
        st = entry.get(key)
        if st:
            return datetime(*st[:6], tzinfo=timezone.utc)
    return None


def _clean(entry) -> str:
    """Feed summaries are often HTML fragments."""
    from bs4 import BeautifulSoup

    raw = entry.get("summary") or entry.get("description") or ""
    return BeautifulSoup(raw, "html.parser").get_text(" ", strip=True)


async def fetch_feed(client: httpx.AsyncClient, spec: SourceSpec, *, lookback_hours: int | None = None,
                     limit: int | None = None) -> list[ArticleIn]:
    lookback = lookback_hours if lookback_hours is not None else settings.ingest_lookback_hours
    limit = limit or settings.max_articles_per_source
    cutoff = datetime.now(tz=timezone.utc) - timedelta(hours=lookback)

    try:
        resp = await client.get(str(spec.feed_url), follow_redirects=True, timeout=20.0)
        resp.raise_for_status()
    except Exception as exc:  # network, 4xx, 5xx — a dead feed must not kill the run
        log.warning("rss.fetch_failed", source=spec.slug, error=str(exc)[:200])
        return []

    parsed = feedparser.parse(resp.content)
    if parsed.bozo and not parsed.entries:
        log.warning("rss.unparseable", source=spec.slug, error=str(parsed.get("bozo_exception"))[:200])
        return []

    out: list[ArticleIn] = []
    for entry in parsed.entries[: limit * 2]:
        url = entry.get("link")
        title = (entry.get("title") or "").strip()
        if not url or not title:
            continue
        published = _parse_dt(entry)
        if published and published < cutoff:
            continue
        out.append(
            ArticleIn(
                source_slug=spec.slug,
                url=url,
                title=title,
                summary=_clean(entry) or None,
                author=entry.get("author"),
                published_at=published,
                lang=spec.lang,
            )
        )
        if len(out) >= limit:
            break

    log.info("rss.fetched", source=spec.slug, entries=len(out))
    return out


async def fetch_all(specs: list[SourceSpec], *, concurrency: int = 8) -> list[ArticleIn]:
    sem = asyncio.Semaphore(concurrency)
    headers = {"User-Agent": settings.http_user_agent}

    async with httpx.AsyncClient(headers=headers) as client:
        async def one(spec: SourceSpec) -> list[ArticleIn]:
            async with sem:
                return await fetch_feed(client, spec)

        results = await asyncio.gather(*(one(s) for s in specs if s.enabled), return_exceptions=True)

    articles: list[ArticleIn] = []
    for r in results:
        if isinstance(r, Exception):
            log.warning("rss.task_failed", error=str(r)[:200])
            continue
        articles.extend(r)
    return articles

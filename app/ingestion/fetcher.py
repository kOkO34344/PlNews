"""Article body extraction.

RSS summaries are usually too thin for real analysis, so we pull the page and run
trafilatura. Failures are non-fatal: the analyst prompt tolerates title+summary only.
Extractions are cached on disk so re-runs of a day cost nothing.
"""
from __future__ import annotations

import asyncio
import hashlib
from pathlib import Path

import httpx
import structlog

from app.config import settings

log = structlog.get_logger(__name__)

CACHE_DIR = Path("./data/cache/bodies")
MAX_BODY_CHARS = 8_000  # what we pass to the LLM per article


def url_hash(url: str) -> str:
    return hashlib.sha256(url.encode("utf-8")).hexdigest()[:32]


def _cache_path(url: str) -> Path:
    h = url_hash(url)
    return CACHE_DIR / h[:2] / f"{h}.txt"


def _read_cache(url: str) -> str | None:
    p = _cache_path(url)
    return p.read_text(encoding="utf-8") if p.exists() else None


def _write_cache(url: str, text: str) -> None:
    p = _cache_path(url)
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(text, encoding="utf-8")


def extract_body(html: str, url: str) -> str | None:
    import trafilatura

    text = trafilatura.extract(html, url=url, include_comments=False, include_tables=False,
                               favor_precision=True)
    return text.strip() if text else None


async def fetch_body(client: httpx.AsyncClient, url: str, *, use_cache: bool = True) -> str | None:
    if use_cache and (cached := _read_cache(url)) is not None:
        return cached or None
    try:
        resp = await client.get(url, follow_redirects=True, timeout=25.0)
        resp.raise_for_status()
        ctype = resp.headers.get("content-type", "")
        if "html" not in ctype:
            return None
        body = extract_body(resp.text, url)
    except Exception as exc:
        log.debug("fetcher.failed", url=url[:120], error=str(exc)[:160])
        body = None

    _write_cache(url, body or "")  # cache misses too: don't re-hammer paywalls
    return body


async def fetch_bodies(urls: list[str], *, concurrency: int = 6) -> dict[str, str]:
    """Returns {url: body}. Missing/failed URLs are simply absent."""
    sem = asyncio.Semaphore(concurrency)
    headers = {"User-Agent": settings.http_user_agent}
    out: dict[str, str] = {}

    async with httpx.AsyncClient(headers=headers) as client:
        async def one(u: str) -> None:
            async with sem:
                body = await fetch_body(client, u)
            if body:
                out[u] = body[:MAX_BODY_CHARS]

        await asyncio.gather(*(one(u) for u in dict.fromkeys(urls)))

    log.info("fetcher.done", requested=len(urls), extracted=len(out))
    return out

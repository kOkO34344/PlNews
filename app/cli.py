"""Operator CLI: `plnews <command>` (or `python -m app.cli <command>`)."""
from __future__ import annotations

import asyncio
import json
from datetime import date

import typer

from app.db import init_db, session_scope

app = typer.Typer(help="3-3-3 Democracy-Aware News Analyst", no_args_is_help=True)


@app.command()
def initdb() -> None:
    """Create tables and load the source registry."""
    from app.ingestion.sources import sync_sources_to_db

    init_db()
    with session_scope() as db:
        added = sync_sources_to_db(db)
    typer.echo(f"schema ready · {added} new sources registered")


@app.command("verify-feeds")
def verify_feeds(include_disabled: bool = typer.Option(False, help="Also probe disabled sources")) -> None:
    """Check every registered feed. Exits non-zero if an *enabled* feed is broken."""
    import asyncio

    import feedparser
    import httpx

    from app.config import settings
    from app.ingestion.sources import SOURCES

    async def _go() -> int:
        broken: list[str] = []
        async with httpx.AsyncClient(headers={"User-Agent": settings.http_user_agent}) as client:
            for s in SOURCES:
                if not s.enabled and not include_disabled:
                    typer.echo(f"skip {s.slug:<20} (disabled — see ownership_note)")
                    continue
                try:
                    r = await client.get(str(s.feed_url), follow_redirects=True, timeout=20)
                    n = len(feedparser.parse(r.content).entries)
                except Exception as exc:
                    n, r = 0, None
                    typer.echo(f"FAIL {s.slug:<20} {type(exc).__name__}: {str(exc)[:60]}")
                else:
                    mark = "ok  " if n else "DEAD"
                    typer.echo(f"{mark} {s.slug:<20} {r.status_code} entries={n}")
                if not n and s.enabled:
                    broken.append(s.slug)

        enabled = [s for s in SOURCES if s.enabled]
        typer.echo(f"\n{len(enabled) - len(broken)}/{len(enabled)} enabled feeds healthy")
        if broken:
            typer.echo(f"broken: {', '.join(broken)}")
        return 1 if broken else 0

    raise typer.Exit(code=asyncio.run(_go()))


@app.command()
def ingest(full_text: bool = True) -> None:
    """Fetch, classify and cluster today's articles without calling the LLM."""
    from app.ingestion.pipeline import run_ingestion

    async def _go() -> None:
        with session_scope() as db:
            result = await run_ingestion(db, fetch_full_text=full_text)
        typer.echo(json.dumps(result.stats, indent=2))
        for cat, clusters in result.clusters.items():
            typer.echo(f"\n{cat.value}:")
            for c in clusters[:10]:
                typer.echo(f"  [{c.source_count} src] {c.headline[:100]}")

    asyncio.run(_go())


@app.command()
def build(dry_run: bool = False, no_markdown: bool = False) -> None:
    """Run the full daily pipeline and store the digest."""
    from app.digest.builder import build_daily_digest

    async def _go() -> None:
        with session_scope() as db:
            digest = await build_daily_digest(db, dry_run=dry_run, write_markdown=not no_markdown)
        typer.echo(f"\n{digest.digest_date}: {len(digest.items)} stories, "
                   f"deep dive: {'yes' if digest.deep_dive else 'no'}")
        for item in digest.items:
            typer.echo(f"  [{item.category.value}] {item.rank}. {item.analysis.headline}")

    asyncio.run(_go())


@app.command()
def show(day: str = typer.Argument(None, help="YYYY-MM-DD, defaults to latest"),
         as_markdown: bool = True) -> None:
    """Print a stored digest."""
    from app import repository as repo
    from app.digest.markdown import render_digest_markdown

    with session_scope() as db:
        digest = repo.get_digest(db, date.fromisoformat(day)) if day else repo.latest_digest(db)
    if digest is None:
        raise typer.Exit(code=1)
    typer.echo(render_digest_markdown(digest) if as_markdown
               else digest.model_dump_json(indent=2))


@app.command()
def translate(lang: str = typer.Argument("bg", help="Target language code"),
              day: str = typer.Option(None, help="YYYY-MM-DD, defaults to latest")) -> None:
    """Translate a stored digest. The analyst writes in English; this renders it."""
    from app import repository as repo
    from app.analysis.llm import get_llm_client
    from app.analysis.translate import translate_digest

    async def _go() -> None:
        # Two short sessions around the slow part: holding one open for the whole LLM run
        # keeps a SQLite write transaction alive for minutes and blocks the API's reads.
        with session_scope() as db:
            digest = repo.get_digest(db, date.fromisoformat(day)) if day else repo.latest_digest(db)
        if digest is None:
            typer.echo("no digest to translate")
            raise typer.Exit(code=1)

        existing = (digest.translations or {}).get(lang)
        result = await translate_digest(get_llm_client(), digest, lang, existing=existing)

        with session_scope() as db:
            repo.save_translation(db, digest.digest_date, lang, result)
        from app.analysis.translate import is_complete

        complete = is_complete(digest, result)
        typer.echo(f"{digest.digest_date} → {lang}: {len(result.items)}/{len(digest.items)} stories"
                   f", deep dive: {'yes' if result.deep_dive else 'no'}"
                   f" — {'complete' if complete else 'incomplete, re-run to resume'}")
        if not complete:
            raise typer.Exit(code=2)   # so a retry wrapper can tell

    asyncio.run(_go())


@app.command()
def push() -> None:
    """Send the latest stored digest to Telegram."""
    from app import repository as repo
    from app.delivery.telegram_bot import push_digest

    async def _go() -> None:
        with session_scope() as db:
            digest = repo.latest_digest(db)
        if digest is None:
            raise typer.Exit(code=1)
        await push_digest(digest)

    asyncio.run(_go())


if __name__ == "__main__":
    app()

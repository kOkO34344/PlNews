"""Daily job runner: python -m app.jobs.scheduler

One cron job builds the digest at DIGEST_HOUR local time and pushes it to Telegram.
A lighter mid-day ingest keeps the article store warm so the morning build is fast.
"""
from __future__ import annotations

import asyncio
import logging

import structlog
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger

from app.config import settings
from app.db import init_db, session_scope

log = structlog.get_logger(__name__)


async def job_build_and_push() -> None:
    from app.delivery.telegram_bot import push_digest
    from app.digest.builder import build_daily_digest

    try:
        with session_scope() as db:
            digest = await build_daily_digest(db)
    except Exception:
        log.exception("job.build_failed")
        return

    if settings.telegram_bot_token and settings.allowed_chat_ids:
        try:
            await push_digest(digest)
        except Exception:
            log.exception("job.push_failed")   # the digest is already stored; delivery can be retried


async def job_ingest_only() -> None:
    from app.ingestion.pipeline import run_ingestion

    try:
        with session_scope() as db:
            await run_ingestion(db)
    except Exception:
        log.exception("job.ingest_failed")


def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(message)s")
    init_db()

    sched = AsyncIOScheduler(timezone=settings.timezone)
    sched.add_job(job_build_and_push, CronTrigger(hour=settings.digest_hour, minute=0),
                  id="daily_digest", misfire_grace_time=3600, coalesce=True)
    sched.add_job(job_ingest_only, CronTrigger(hour="12,18", minute=30), id="warm_ingest",
                  misfire_grace_time=900, coalesce=True)
    sched.start()
    log.info("scheduler.started", hour=settings.digest_hour, tz=settings.timezone)

    loop = asyncio.get_event_loop()
    try:
        loop.run_forever()
    except (KeyboardInterrupt, SystemExit):
        log.info("scheduler.stopping")


if __name__ == "__main__":
    main()

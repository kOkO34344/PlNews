"""Phase 1 of the daily run: fetch → filter → classify → cluster → persist.

Returns the clusters worth spending LLM tokens on, already stored with their
articles attached and continuity links to yesterday's running stories.
"""
from __future__ import annotations

from dataclasses import dataclass, field

import structlog

from app.config import settings
from app.ingestion import classify, dedupe, rss
from app.ingestion.fetcher import fetch_bodies
from app.ingestion.sources import SOURCES, sync_sources_to_db
from app.models.schemas import ArticleIn, Category, StoryClusterIn

log = structlog.get_logger(__name__)

# How many clusters per category we are willing to analyse. The 3-3-3 selection then
# picks the top 3 of these — a wider funnel costs tokens, a narrower one costs recall.
ANALYSIS_CANDIDATES_PER_CATEGORY = 12
MIN_SOURCES_FOR_CANDIDATE = 1


@dataclass
class IngestResult:
    clusters: dict[Category, list[StoryClusterIn]] = field(default_factory=dict)
    article_ids: dict[str, int] = field(default_factory=dict)
    bodies: dict[str, str] = field(default_factory=dict)
    stats: dict[str, int] = field(default_factory=dict)

    @property
    def all_clusters(self) -> list[StoryClusterIn]:
        return [c for cs in self.clusters.values() for c in cs]


async def run_ingestion(session, *, fetch_full_text: bool = True) -> IngestResult:
    sync_sources_to_db(session)

    raw = await rss.fetch_all(SOURCES)
    log.info("pipeline.fetched", articles=len(raw))

    kept = [a for a in raw if not classify.is_noise(a)]
    kept = dedupe.drop_near_duplicates(kept)

    categories: dict[str, Category] = {}
    for a in kept:
        cat = classify.classify(a)
        if cat:
            categories[a.url] = cat
    kept = [a for a in kept if a.url in categories]
    log.info("pipeline.classified", kept=len(kept))

    clusters = dedupe.cluster_by_category(kept, categories)

    # Trim to the analysis funnel before paying for full-text extraction.
    trimmed: dict[Category, list[StoryClusterIn]] = {}
    for cat, cs in clusters.items():
        cs = [c for c in cs if c.source_count >= MIN_SOURCES_FOR_CANDIDATE]
        trimmed[cat] = cs[:ANALYSIS_CANDIDATES_PER_CATEGORY]

    bodies: dict[str, str] = {}
    if fetch_full_text:
        urls = [ref.url for cs in trimmed.values() for c in cs for ref in c.articles]
        bodies = await fetch_bodies(urls)

    # Persist articles (with bodies) and clusters.
    by_url = {a.url: a for a in kept}
    for url, body in bodies.items():
        if url in by_url:
            by_url[url] = _with_body(by_url[url], body)

    from app import repository as repo

    article_ids = repo.upsert_articles(session, list(by_url.values()))
    previous = repo.previous_cluster_keys(session, days=4)
    for cs in trimmed.values():
        for c in cs:
            parent = dedupe.match_continuity(c, previous)
            repo.upsert_cluster(session, c, article_ids, parent_key=parent)

    stats = {
        "fetched": len(raw),
        "kept": len(kept),
        "clusters": sum(len(v) for v in trimmed.values()),
        "bodies_extracted": len(bodies),
        "sources": len([s for s in SOURCES if s.enabled]),
    }
    log.info("pipeline.done", **stats)
    return IngestResult(clusters=trimmed, article_ids=article_ids, bodies=bodies, stats=stats)


def _with_body(article: ArticleIn, body: str) -> ArticleIn:
    return article.model_copy(update={"body": body})

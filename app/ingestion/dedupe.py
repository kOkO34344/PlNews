"""De-duplication and story clustering.

Two layers:
  1. `simhash` on normalized title+lede kills syndicated near-identical copies fast.
  2. TF-IDF cosine similarity with greedy agglomeration groups different outlets'
     coverage of the same event into one `StoryClusterIn`.

Deliberately dependency-light and deterministic — no embeddings API call in the hot
path. `EmbeddingBackend` is the seam if you later want semantic clustering.
"""
from __future__ import annotations

import hashlib
import re
import unicodedata
from collections import defaultdict
from datetime import datetime, timezone
from typing import Protocol

import structlog

from app.ingestion.sources import BY_SLUG
from app.models.schemas import ArticleIn, ArticleRef, Category, StoryClusterIn

log = structlog.get_logger(__name__)

SIM_THRESHOLD = 0.42        # TF-IDF cosine similarity to merge into one story
OVERLAP_THRESHOLD = 0.5     # token containment fallback: short headlines dilute TF-IDF
MIN_SHARED_TOKENS = 3       # guard against 0.5 containment on two-word titles
SIMHASH_DISTANCE = 4        # hamming distance treated as "same article"
_TOKEN = re.compile(r"[^\w\s]", re.UNICODE)

STOPWORDS = {
    "the", "a", "an", "of", "in", "on", "for", "to", "and", "with", "at", "by", "from", "as", "is",
    "are", "was", "were", "said", "says", "after", "over", "new",
    "и", "в", "на", "за", "с", "от", "по", "че", "се", "да", "е", "са", "не", "но", "като", "след",
}


def normalize(text: str) -> str:
    text = unicodedata.normalize("NFKC", text or "").lower()
    text = _TOKEN.sub(" ", text)
    return " ".join(w for w in text.split() if w not in STOPWORDS and len(w) > 2)


def simhash(text: str, bits: int = 64) -> int:
    """Classic Charikar simhash over token shingles."""
    tokens = normalize(text).split()
    if not tokens:
        return 0
    vec = [0] * bits
    for tok in tokens:
        h = int(hashlib.blake2b(tok.encode("utf-8"), digest_size=8).hexdigest(), 16)
        for i in range(bits):
            vec[i] += 1 if (h >> i) & 1 else -1
    out = 0
    for i, v in enumerate(vec):
        if v > 0:
            out |= 1 << i
    return out


def hamming(a: int, b: int) -> int:
    return bin(a ^ b).count("1")


class EmbeddingBackend(Protocol):
    """Seam for swapping TF-IDF for real embeddings later."""
    def encode(self, texts: list[str]) -> list[list[float]]: ...


def _ref(article: ArticleIn, article_id: int | None = None) -> ArticleRef:
    spec = BY_SLUG.get(article.source_slug)
    return ArticleRef(
        id=article_id,
        source_slug=article.source_slug,
        source_name=spec.name if spec else article.source_slug,
        lean=spec.lean if spec else "unknown",          # type: ignore[arg-type]
        reliability=spec.reliability if spec else "medium",  # type: ignore[arg-type]
        title=article.title,
        url=article.url,
        published_at=article.published_at,
    )


def drop_near_duplicates(articles: list[ArticleIn]) -> list[ArticleIn]:
    """Keep one article per (near-identical text, source) — wire copy-paste."""
    kept: list[tuple[int, ArticleIn]] = []
    for a in articles:
        h = simhash(f"{a.title} {(a.summary or '')[:400]}")
        if any(hamming(h, kh) <= SIMHASH_DISTANCE and ka.source_slug == a.source_slug
               for kh, ka in kept):
            continue
        kept.append((h, a))
    dropped = len(articles) - len(kept)
    if dropped:
        log.info("dedupe.near_duplicates_dropped", n=dropped)
    return [a for _, a in kept]


def token_containment(a: set[str], b: set[str]) -> float:
    """|A∩B| / min(|A|,|B|) — robust where TF-IDF is not, i.e. on bare headlines."""
    if not a or not b:
        return 0.0
    shared = a & b
    if len(shared) < MIN_SHARED_TOKENS:
        return 0.0
    return len(shared) / min(len(a), len(b))


def cluster_articles(articles: list[ArticleIn], category: Category) -> list[StoryClusterIn]:
    """Greedy agglomeration within one category.

    Two articles join the same story if either TF-IDF cosine or token containment clears
    its threshold. Headlines are short enough that IDF alone under-merges obvious pairs
    ("Parliament passes X" / "MPs pass X"), so containment carries the short-text case.
    """
    if not articles:
        return []

    from sklearn.feature_extraction.text import TfidfVectorizer
    from sklearn.metrics.pairwise import cosine_similarity

    docs = [normalize(f"{a.title} {a.summary or ''}") for a in articles]
    token_sets = [set(normalize(a.title).split()) for a in articles]

    if len(docs) == 1:
        sims = [[1.0]]
    else:
        vec = TfidfVectorizer(max_features=20_000, ngram_range=(1, 2), min_df=1, sublinear_tf=True)
        matrix = vec.fit_transform(docs)
        sims = cosine_similarity(matrix)

    def same_story(i: int, j: int) -> bool:
        return (sims[i][j] >= SIM_THRESHOLD
                or token_containment(token_sets[i], token_sets[j]) >= OVERLAP_THRESHOLD)

    assigned: dict[int, int] = {}
    groups: list[list[int]] = []
    for i in range(len(articles)):
        if i in assigned:
            continue
        gid = len(groups)
        groups.append([i])
        assigned[i] = gid
        for j in range(i + 1, len(articles)):
            if j not in assigned and same_story(i, j):
                assigned[j] = gid
                groups[gid].append(j)

    clusters: list[StoryClusterIn] = []
    for members in groups:
        items = [articles[i] for i in members]
        # Headline seed: highest-weight source, then longest title (usually most informative).
        seed = max(items, key=lambda a: ((BY_SLUG.get(a.source_slug).weight if BY_SLUG.get(a.source_slug) else 1.0),
                                         len(a.title)))
        stamps = [a.published_at for a in items if a.published_at] or [datetime.now(tz=timezone.utc)]
        key = hashlib.sha256(("|".join(sorted(a.url for a in items))).encode()).hexdigest()[:32]
        clusters.append(
            StoryClusterIn(
                key=key,
                category=category,
                headline=seed.title[:300],
                articles=[_ref(a) for a in items],
                first_seen=min(stamps),
                last_seen=max(stamps),
            )
        )

    clusters.sort(key=lambda c: (c.source_count, len(c.articles)), reverse=True)
    log.info("dedupe.clustered", category=category.value, articles=len(articles), clusters=len(clusters))
    return clusters


def cluster_by_category(articles: list[ArticleIn],
                        categories: dict[str, Category]) -> dict[Category, list[StoryClusterIn]]:
    """`categories` maps article.url -> Category (from app.ingestion.classify)."""
    buckets: dict[Category, list[ArticleIn]] = defaultdict(list)
    for a in articles:
        cat = categories.get(a.url)
        if cat:
            buckets[cat].append(a)
    return {cat: cluster_articles(items, cat) for cat, items in buckets.items()}


def match_continuity(cluster: StoryClusterIn, previous: list[tuple[str, str]]) -> str | None:
    """Link today's cluster to yesterday's running story. `previous` is [(key, headline)]."""
    if not previous:
        return None
    today = set(normalize(cluster.headline).split())
    best_key, best_score = None, 0.0
    for key, headline in previous:
        prior = set(normalize(headline).split())
        if not prior or not today:
            continue
        jaccard = len(today & prior) / len(today | prior)
        if jaccard > best_score:
            best_key, best_score = key, jaccard
    return best_key if best_score >= 0.35 else None

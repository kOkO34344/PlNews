"""Cheap, deterministic category routing.

Runs before the LLM so we never pay tokens to discover an article is off-topic.
Source categories are the prior; keyword evidence can override when a source
covers more than one of our three buckets.
"""
from __future__ import annotations

import re

from app.ingestion.sources import BY_SLUG
from app.models.schemas import ArticleIn, Category

KEYWORDS: dict[Category, list[str]] = {
    Category.BG_POLITICS: [
        "българия", "народното събрание", "парламент", "министерски съвет", "герб", "пп-дб",
        "възраждане", "дпс", "бсп", "итн", "президент", "радев", "борисов", "пеевски", "прокуратура",
        "кпк", "антикорупционн", "изборите", "цик", "конституц", "вот на недоверие", "бюджет",
        "bulgaria", "bulgarian", "sofia", "gerb", "peevski", "borissov", "radev",
    ],
    Category.GLOBAL_POLITICS: [
        "european commission", "european parliament", "nato", "ukraine", "russia", "china", "election",
        "sanctions", "rule of law", "eu council", "referendum", "coalition", "parliament", "supreme court",
        "president", "prime minister", "war", "ceasefire", "protest", "coup", "impeach",
    ],
    Category.AI_TECH_BUSINESS: [
        "ai", "artificial intelligence", "llm", "openai", "anthropic", "google", "microsoft", "nvidia",
        "chip", "semiconductor", "startup", "funding round", "ipo", "acquisition", "antitrust",
        "data centre", "data center", "cloud", "privacy", "gdpr", "ai act", "model", "compute",
        "cyber", "breach", "encryption", "platform", "regulation",
    ],
}

_WORD = re.compile(r"[\w']+", re.UNICODE)


def _score(text: str, terms: list[str]) -> int:
    t = text.lower()
    return sum(1 for term in terms if term in t)


def classify(article: ArticleIn) -> Category | None:
    """Return the best category, or None if the article does not belong in the digest."""
    spec = BY_SLUG.get(article.source_slug)
    haystack = " ".join(filter(None, [article.title, article.summary or "", (article.body or "")[:1200]]))

    scores = {cat: _score(haystack, terms) for cat, terms in KEYWORDS.items()}

    # Source prior: a single-category source wins unless another category scores clearly higher.
    if spec and len(spec.categories) == 1:
        prior = spec.categories[0]
        best_other = max((c for c in scores if c != prior), key=lambda c: scores[c])
        if scores[best_other] >= scores[prior] + 3:
            return best_other
        return prior

    if spec:
        allowed = {c: scores[c] for c in spec.categories}
        best = max(allowed, key=lambda c: allowed[c])
        return best if allowed[best] > 0 else spec.categories[0]

    best = max(scores, key=lambda c: scores[c])
    return best if scores[best] >= 2 else None


def is_noise(article: ArticleIn) -> bool:
    """Filter out horoscopes, sports, celebrity churn and press-release padding."""
    noise_terms = (
        "хороскоп", "спорт", "футбол", "цска", "левски", "тото", "времето", "vremeto",
        "horoscope", "recipe", "deals of the day", "best deals", "sponsored", "advertorial",
        "coupon", "black friday", "gift guide",
    )
    t = (article.title or "").lower()
    return any(n in t for n in noise_terms)

"""Phase 3: pick the 3-3-3.

Three stories per category, chosen by a transparent weighted score plus diversity
constraints. Every selection carries its own breakdown so the digest can explain
*why* a story made the cut — the alternative is an unauditable black box.

    total = w_dem·democracy + w_imp·impact + w_nov·novelty + w_cred·credibility
            + w_per·personal − penalties
"""
from __future__ import annotations

from dataclasses import dataclass

import structlog

from app.analysis.analyzer import AnalysisOutcome
from app.analysis.democracy import democracy_score, sanity_flags
from app.config import settings
from app.ingestion.sources import RELIABILITY_WEIGHT
from app.models.schemas import Category, DigestItem, SelectionScore, StoryAnalysis

log = structlog.get_logger(__name__)

PER_CATEGORY = 3

# Penalties keep the digest honest and varied.
P_SINGLE_SOURCE = 0.08          # one outlet only
P_LOW_DIVERSITY = 0.06          # all sources share a lean
P_SANITY_FLAG = 0.05            # per flag from democracy.sanity_flags
P_REPEAT_STORY = 0.10           # ran in yesterday's digest with little new
P_ENTITY_CROWDING = 0.07        # third+ story about the same actor in one digest


@dataclass
class Candidate:
    outcome: AnalysisOutcome
    score: SelectionScore

    @property
    def analysis(self) -> StoryAnalysis:
        assert self.outcome.analysis is not None
        return self.outcome.analysis


def _source_credibility(outcome: AnalysisOutcome) -> float:
    refs = outcome.cluster.articles
    if not refs:
        return 0.0
    best = max(RELIABILITY_WEIGHT.get(r.reliability, 0.5) for r in refs)
    breadth = min(len({r.source_slug for r in refs}) / 4.0, 1.0)
    return round(0.6 * best + 0.4 * breadth, 4)


def _personal_score(analysis: StoryAnalysis, interests: dict[str, float]) -> float:
    if not interests:
        return 0.5
    hits = [interests[t] for t in (*analysis.tags, *analysis.entities) if t in interests]
    if not hits:
        return 0.5
    return max(0.0, min(1.0, 0.5 + sum(hits) / len(hits)))


def score_candidate(outcome: AnalysisOutcome, interests: dict[str, float],
                    repeated_keys: set[str]) -> SelectionScore:
    a = outcome.analysis
    assert a is not None

    dem = democracy_score(a)
    impact = a.impact_scope
    novelty = a.novelty
    cred = round(0.5 * a.credibility + 0.5 * _source_credibility(outcome), 4)
    personal = _personal_score(a, interests)

    penalties = 0.0
    reasons: list[str] = []
    if outcome.cluster.source_count <= 1:
        penalties += P_SINGLE_SOURCE
        reasons.append("single source")
    leans = {r.lean for r in outcome.cluster.articles}
    if len(leans) <= 1 and outcome.cluster.source_count > 1:
        penalties += P_LOW_DIVERSITY
        reasons.append("one editorial lean")
    flags = sanity_flags(a)
    if flags:
        penalties += P_SANITY_FLAG * len(flags)
        reasons.append(f"flags: {', '.join(flags)}")
    if outcome.cluster.key in repeated_keys and a.novelty < 0.4:
        penalties += P_REPEAT_STORY
        reasons.append("ran yesterday, little new")

    total = (
        settings.w_democracy * dem
        + settings.w_impact * impact
        + settings.w_novelty * novelty
        + settings.w_credibility * cred
        + settings.w_personal * personal
        - penalties
    )

    explanation = (
        f"democracy {dem:.2f} · impact {impact:.2f} · novelty {novelty:.2f} · "
        f"credibility {cred:.2f} · fit {personal:.2f}"
        + (f" · −{penalties:.2f} ({'; '.join(reasons)})" if penalties else "")
    )
    return SelectionScore(cluster_key=outcome.cluster.key, total=round(total, 4), democracy=dem,
                          impact=impact, novelty=novelty, credibility=cred, personal=personal,
                          penalties=round(penalties, 4), explanation=explanation)


def select_category(outcomes: list[AnalysisOutcome], category: Category,
                    interests: dict[str, float], repeated_keys: set[str],
                    used_entities: set[str]) -> list[DigestItem]:
    """Top 3 for one category, with entity-crowding applied greedily."""
    cands = [
        Candidate(o, score_candidate(o, interests, repeated_keys))
        for o in outcomes
        if o.analysis is not None and o.analysis.category == category
    ]
    cands.sort(key=lambda c: c.score.total, reverse=True)

    picked: list[Candidate] = []
    local_entities: set[str] = set(used_entities)
    for cand in cands:
        if len(picked) >= PER_CATEGORY:
            break
        ents = {e.lower() for e in cand.analysis.entities[:3]}
        crowding = len(ents & local_entities)
        if crowding and len(cands) > PER_CATEGORY + 1:
            adjusted = cand.score.total - P_ENTITY_CROWDING * crowding
            # Only skip if a genuinely competitive alternative exists.
            better = [c for c in cands if c not in picked and c.score.total > adjusted
                      and not ({e.lower() for e in c.analysis.entities[:3]} & local_entities)]
            if better:
                continue
        picked.append(cand)
        local_entities |= ents

    used_entities |= local_entities

    items: list[DigestItem] = []
    for rank, cand in enumerate(picked, start=1):
        items.append(DigestItem(rank=rank, category=category, analysis=cand.analysis,
                                score=cand.score, refs=cand.outcome.cluster.articles))
    log.info("selector.category", category=category.value, candidates=len(cands), picked=len(items))
    return items


def select_333(outcomes: list[AnalysisOutcome], *, interests: dict[str, float] | None = None,
               repeated_keys: set[str] | None = None) -> list[DigestItem]:
    interests = interests or {}
    repeated_keys = repeated_keys or set()
    used_entities: set[str] = set()

    items: list[DigestItem] = []
    for cat in (Category.BG_POLITICS, Category.GLOBAL_POLITICS, Category.AI_TECH_BUSINESS):
        items.extend(select_category(outcomes, cat, interests, repeated_keys, used_entities))

    short = [c.value for c in Category if len([i for i in items if i.category == c]) < PER_CATEGORY]
    if short:
        log.warning("selector.underfilled", categories=short,
                    msg="fewer than 3 candidates survived — digest will be short for these")
    return items

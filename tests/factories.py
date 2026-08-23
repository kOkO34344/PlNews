"""Deterministic fixtures so tests never touch the network or an LLM."""
from __future__ import annotations

from datetime import datetime, timedelta, timezone

from app.models.schemas import (
    ArticleIn, ArticleRef, BiasAssessment, Category, Claim, ClaimStatus, DemocracyAssessment,
    DemocracyDimension, DemocracyImpact, Lean, Reliability, Scenario, DeepDive, StoryAnalysis,
    StoryClusterIn,
)

NOW = datetime(2026, 8, 23, 9, 0, tzinfo=timezone.utc)


def make_article(slug: str = "dnevnik", title: str = "Parliament votes on judicial reform",
                 url: str | None = None, minutes_ago: int = 30) -> ArticleIn:
    return ArticleIn(
        source_slug=slug,
        url=url or f"https://example.org/{slug}/{abs(hash(title)) % 10**8}",
        title=title,
        summary=f"{title}. Details follow.",
        published_at=NOW - timedelta(minutes=minutes_ago),
    )


def make_ref(slug: str = "dnevnik", name: str = "Dnevnik", lean: Lean = Lean.CENTER,
             reliability: Reliability = Reliability.HIGH, title: str = "Headline") -> ArticleRef:
    return ArticleRef(source_slug=slug, source_name=name, lean=lean, reliability=reliability,
                      title=title, url=f"https://example.org/{slug}/1", published_at=NOW)


def make_cluster(key: str = "k1", category: Category = Category.BG_POLITICS,
                 refs: list[ArticleRef] | None = None) -> StoryClusterIn:
    refs = refs or [make_ref(), make_ref("mediapool", "Mediapool", Lean.CENTER)]
    return StoryClusterIn(key=key, category=category, headline="Parliament votes on judicial reform",
                          articles=refs, first_seen=NOW, last_seen=NOW)


def make_analysis(key: str = "k1", category: Category = Category.BG_POLITICS, *,
                  significance: float = 0.8, direction: int = -1, novelty: float = 0.7,
                  credibility: float = 0.8, impact: float = 0.6,
                  entities: list[str] | None = None) -> StoryAnalysis:
    return StoryAnalysis(
        cluster_key=key,
        category=category,
        headline="Parliament votes on judicial reform",
        what_happened="The National Assembly passed amendments on second reading by 128 votes to 96.",
        why_it_matters="The amendments change how the prosecutor general can be investigated.",
        claims=[Claim(text="The vote was 128-96.", status=ClaimStatus.ESTABLISHED,
                      evidence="Parliamentary record")],
        democracy=DemocracyAssessment(
            relevant=True,
            impacts=[DemocracyImpact(dimension=DemocracyDimension.RULE_OF_LAW, direction=direction,
                                     rationale="Removes an existing check on prosecutorial power.",
                                     confidence=0.7)],
            net_direction=direction,
            significance=significance,
            precedent="Comparable to the 2016 Polish prosecution service merger.",
            watch_next=["Constitutional Court referral"],
        ),
        bias=BiasAssessment(
            coverage_spread="Government-aligned outlets led with efficiency; independents led with oversight.",
            framing_devices=["passive voice on who benefits"],
            omitted_context=["the pending Venice Commission opinion"],
            source_diversity=0.7,
            propaganda_markers=[],
        ),
        entities=entities or ["National Assembly", "Prosecutor General"],
        impact_scope=impact,
        novelty=novelty,
        credibility=credibility,
        uncertainty="The Constitutional Court's position is unknown.",
        contrarian_read="The amendments may simply codify existing practice.",
        tags=["judiciary", "rule-of-law"],
    )


def make_deep_dive(key: str = "k1") -> DeepDive:
    return DeepDive(
        cluster_key=key,
        title="Judicial reform and the prosecutor general",
        executive_summary="Parliament moved to change oversight of the prosecution service.",
        background="A two-year dispute over prosecutorial accountability.",
        stakeholders=["Governing coalition — wants control — has the votes"],
        mechanisms="Amendments to the Judicial System Act, second reading.",
        democracy_analysis="Reduces an existing check without adding an alternative.",
        comparative_precedent="Poland 2015-2023, with important differences.",
        scenarios=[
            Scenario(name="Court strikes it down", probability=0.4, description="Referral succeeds.",
                     early_indicators=["Referral filed within 14 days"]),
            Scenario(name="Law stands", probability=0.6, description="No referral or it fails.",
                     early_indicators=["No referral by deadline"]),
        ],
        what_to_watch=["Venice Commission opinion"],
        open_questions=["Who initiates investigations under the new text?"],
        counterargument="The prior mechanism was never used, so little changes in practice.",
        confidence=0.6,
    )

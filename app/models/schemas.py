"""Pydantic v2 domain models.

These double as the *contract* for LLM output: `StoryAnalysis` and `DeepDive` are
dumped to JSON Schema and injected into the prompts, and every LLM response is
validated against them before it is allowed anywhere near the database.
"""
from __future__ import annotations

from datetime import date, datetime
from enum import StrEnum
from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field, HttpUrl, field_validator

Score = Annotated[float, Field(ge=0.0, le=1.0)]
Impact = Annotated[int, Field(ge=-2, le=2)]  # -2 erosive ... +2 strengthening


# --------------------------------------------------------------------------- #
# Taxonomy
# --------------------------------------------------------------------------- #
class Category(StrEnum):
    BG_POLITICS = "bg_politics"
    GLOBAL_POLITICS = "global_politics"
    AI_TECH_BUSINESS = "ai_tech_business"


class Lean(StrEnum):
    """Editorial prior of a *source*, not a verdict on any single article."""
    LEFT = "left"
    CENTER_LEFT = "center_left"
    CENTER = "center"
    CENTER_RIGHT = "center_right"
    RIGHT = "right"
    STATE_ALIGNED = "state_aligned"      # government/party-owned or captured outlet
    OLIGARCH_LINKED = "oligarch_linked"  # BG-specific: known ownership capture
    UNKNOWN = "unknown"


class Reliability(StrEnum):
    HIGH = "high"          # wire services, outlets with corrections policy
    MEDIUM = "medium"
    LOW = "low"            # aggregators, heavy churnalism
    PROPAGANDA = "propaganda"


class DemocracyDimension(StrEnum):
    """Rubric adapted from V-Dem / Bright Line Watch style indicators."""
    RULE_OF_LAW = "rule_of_law"
    CHECKS_AND_BALANCES = "checks_and_balances"
    ELECTORAL_INTEGRITY = "electoral_integrity"
    MEDIA_FREEDOM = "media_freedom"
    CIVIL_LIBERTIES = "civil_liberties"
    ANTICORRUPTION = "anticorruption"
    MINORITY_RIGHTS = "minority_rights"
    CIVIC_SPACE = "civic_space"
    INFORMATION_INTEGRITY = "information_integrity"  # disinfo, platform capture, AI
    STATE_CAPACITY = "state_capacity"


class ClaimStatus(StrEnum):
    ESTABLISHED = "established"    # multiple independent outlets / primary document
    REPORTED = "reported"          # single-sourced, attributed
    CONTESTED = "contested"        # sources disagree
    SPECULATIVE = "speculative"    # projection, anonymous source, opinion


# --------------------------------------------------------------------------- #
# Ingestion
# --------------------------------------------------------------------------- #
class SourceSpec(BaseModel):
    """Static registry entry (see app/ingestion/sources.py)."""
    slug: str
    name: str
    feed_url: HttpUrl
    homepage: HttpUrl | None = None
    lang: Literal["bg", "en"] = "en"
    country: str = "INT"
    categories: list[Category]
    lean: Lean = Lean.UNKNOWN
    reliability: Reliability = Reliability.MEDIUM
    ownership_note: str | None = None
    weight: float = 1.0            # ingestion priority / credibility multiplier
    enabled: bool = True


class ArticleIn(BaseModel):
    """Normalized article as it leaves the fetchers."""
    source_slug: str
    url: str
    title: str
    summary: str | None = None
    body: str | None = None
    author: str | None = None
    published_at: datetime | None = None
    lang: str = "en"

    @field_validator("title", "summary", "body")
    @classmethod
    def _strip(cls, v: str | None) -> str | None:
        return v.strip() if isinstance(v, str) else v


class ArticleRef(BaseModel):
    """Compact citation used inside analyses and digests."""
    id: int | None = None
    source_slug: str
    source_name: str
    lean: Lean = Lean.UNKNOWN
    reliability: Reliability = Reliability.MEDIUM
    title: str
    url: str
    published_at: datetime | None = None


class StoryClusterIn(BaseModel):
    """A group of articles judged to cover the same underlying event."""
    key: str                    # stable hash of the cluster seed
    category: Category
    headline: str               # neutral, de-spun working title
    articles: list[ArticleRef]
    first_seen: datetime
    last_seen: datetime

    @property
    def source_count(self) -> int:
        return len({a.source_slug for a in self.articles})


# --------------------------------------------------------------------------- #
# LLM analysis contract
# --------------------------------------------------------------------------- #
class DemocracyImpact(BaseModel):
    model_config = ConfigDict(extra="forbid")
    dimension: DemocracyDimension
    direction: Impact = Field(description="-2 strongly erosive, 0 neutral, +2 strongly strengthening")
    rationale: str = Field(max_length=600, description="One or two sentences, tied to specific facts.")
    confidence: Score


class DemocracyAssessment(BaseModel):
    model_config = ConfigDict(extra="forbid")
    relevant: bool = Field(description="False for stories with no meaningful democratic dimension.")
    impacts: list[DemocracyImpact] = Field(default_factory=list, max_length=4)
    net_direction: Impact = 0
    significance: Score = Field(description="How much this matters for democratic health, 0-1.")
    precedent: str | None = Field(default=None, max_length=600,
                                  description="Closest historical or comparative precedent, if any.")
    watch_next: list[str] = Field(default_factory=list, max_length=3,
                                  description="Concrete observable events that would confirm/disconfirm.")


class BiasAssessment(BaseModel):
    model_config = ConfigDict(extra="forbid")
    coverage_spread: str = Field(max_length=400,
                                 description="How outlets across the spectrum framed this differently.")
    framing_devices: list[str] = Field(default_factory=list, max_length=5,
                                       description="Loaded terms, passive voice on agency, selective numbers.")
    omitted_context: list[str] = Field(default_factory=list, max_length=4)
    source_diversity: Score = Field(description="0 = single outlet/echo, 1 = broad independent confirmation.")
    propaganda_markers: list[str] = Field(default_factory=list, max_length=4,
                                          description="Whataboutism, manufactured urgency, anonymous 'experts'.")


class Claim(BaseModel):
    model_config = ConfigDict(extra="forbid")
    text: str = Field(max_length=300)
    status: ClaimStatus
    evidence: str | None = Field(default=None, max_length=400)


class StoryAnalysis(BaseModel):
    """Exact JSON the analysis prompt must return."""
    model_config = ConfigDict(extra="forbid")

    cluster_key: str
    category: Category
    headline: str = Field(max_length=140, description="Neutral, factual, no clickbait.")
    what_happened: str = Field(max_length=900, description="2-4 sentences of verified fact only.")
    why_it_matters: str = Field(max_length=700)
    claims: list[Claim] = Field(default_factory=list, max_length=6)
    democracy: DemocracyAssessment
    bias: BiasAssessment
    entities: list[str] = Field(default_factory=list, max_length=10)
    impact_scope: Score = Field(description="How many people / how durably affected.")
    novelty: Score = Field(description="1 = genuinely new; 0 = rehash of an ongoing story.")
    credibility: Score = Field(description="Confidence the reported facts are accurate.")
    uncertainty: str | None = Field(default=None, max_length=400,
                                    description="What we do NOT know yet. Say so plainly.")
    contrarian_read: str | None = Field(default=None, max_length=500,
                                        description="The strongest good-faith alternative interpretation.")
    tags: list[str] = Field(default_factory=list, max_length=8)


class Scenario(BaseModel):
    model_config = ConfigDict(extra="forbid")
    name: str = Field(max_length=80)
    probability: Score
    description: str = Field(max_length=500)
    early_indicators: list[str] = Field(default_factory=list, max_length=3)


class DeepDive(BaseModel):
    """Exact JSON the deep-dive prompt must return."""
    model_config = ConfigDict(extra="forbid")

    cluster_key: str
    title: str = Field(max_length=140)
    executive_summary: str = Field(max_length=1200)
    background: str = Field(max_length=2500, description="How we got here; the 6-24 month arc.")
    stakeholders: list[str] = Field(default_factory=list, max_length=8,
                                    description="'Actor — interest — leverage' per line.")
    mechanisms: str = Field(max_length=1800,
                            description="The institutional machinery: which law, which body, which veto point.")
    democracy_analysis: str = Field(max_length=2000)
    comparative_precedent: str = Field(max_length=1500,
                                       description="Hungary/Poland/Serbia/Georgia-style comparisons where apt.")
    scenarios: list[Scenario] = Field(min_length=2, max_length=4)
    what_to_watch: list[str] = Field(default_factory=list, max_length=6)
    open_questions: list[str] = Field(default_factory=list, max_length=5)
    counterargument: str = Field(max_length=1000,
                                 description="Steelman of the reading opposite to this analysis.")
    confidence: Score


# --------------------------------------------------------------------------- #
# Selection + digest
# --------------------------------------------------------------------------- #
class SelectionScore(BaseModel):
    cluster_key: str
    total: float
    democracy: float
    impact: float
    novelty: float
    credibility: float
    personal: float
    penalties: float = 0.0
    explanation: str = ""


class DigestItem(BaseModel):
    rank: int = Field(ge=1, le=3)
    category: Category
    analysis: StoryAnalysis
    score: SelectionScore
    refs: list[ArticleRef]


class DigestTranslation(BaseModel):
    """A digest rendered in another language.

    Whole `StoryAnalysis` objects rather than loose strings: the UI swaps
    `item.analysis` wholesale, so a translated rationale cannot end up attached to the
    wrong dimension.
    """
    editorial_note: str | None = None
    items: dict[str, StoryAnalysis] = Field(default_factory=dict)
    deep_dive: DeepDive | None = None


class DailyDigest(BaseModel):
    digest_date: date
    generated_at: datetime
    items: list[DigestItem]
    deep_dive: DeepDive | None = None
    deep_dive_refs: list[ArticleRef] = Field(default_factory=list)
    stats: dict[str, int | float] = Field(default_factory=dict)
    editorial_note: str | None = None
    translations: dict[str, DigestTranslation] = Field(default_factory=dict)

    def by_category(self, category: Category) -> list[DigestItem]:
        return sorted((i for i in self.items if i.category == category), key=lambda i: i.rank)

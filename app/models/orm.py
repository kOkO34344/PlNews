"""SQLAlchemy 2.0 ORM.

Rich LLM output is stored as JSON columns (validated by Pydantic on the way in
and out) while the fields we filter/sort/join on are promoted to real columns.
"""
from __future__ import annotations

from datetime import date, datetime, timezone

from sqlalchemy import (
    JSON, Boolean, Date, DateTime, Float, ForeignKey, Index, Integer, String, Text, UniqueConstraint,
)
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


def utcnow() -> datetime:
    return datetime.now(tz=timezone.utc)


class Base(DeclarativeBase):
    pass


class Source(Base):
    __tablename__ = "sources"

    id: Mapped[int] = mapped_column(primary_key=True)
    slug: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    name: Mapped[str] = mapped_column(String(200))
    feed_url: Mapped[str] = mapped_column(String(500))
    homepage: Mapped[str | None] = mapped_column(String(500))
    lang: Mapped[str] = mapped_column(String(8), default="en")
    country: Mapped[str] = mapped_column(String(8), default="INT")
    categories: Mapped[list] = mapped_column(JSON, default=list)
    lean: Mapped[str] = mapped_column(String(32), default="unknown")
    reliability: Mapped[str] = mapped_column(String(32), default="medium")
    ownership_note: Mapped[str | None] = mapped_column(Text)
    weight: Mapped[float] = mapped_column(Float, default=1.0)
    enabled: Mapped[bool] = mapped_column(Boolean, default=True)
    last_fetched_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    last_error: Mapped[str | None] = mapped_column(Text)

    articles: Mapped[list["Article"]] = relationship(back_populates="source")


class Article(Base):
    __tablename__ = "articles"
    __table_args__ = (
        Index("ix_articles_published", "published_at"),
        Index("ix_articles_cluster", "cluster_id"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    source_id: Mapped[int] = mapped_column(ForeignKey("sources.id"))
    url_hash: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    url: Mapped[str] = mapped_column(String(1000))
    title: Mapped[str] = mapped_column(Text)
    summary: Mapped[str | None] = mapped_column(Text)
    body: Mapped[str | None] = mapped_column(Text)
    author: Mapped[str | None] = mapped_column(String(300))
    lang: Mapped[str] = mapped_column(String(8), default="en")
    published_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    fetched_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    simhash: Mapped[str | None] = mapped_column(String(32), index=True)
    cluster_id: Mapped[int | None] = mapped_column(ForeignKey("clusters.id"))

    source: Mapped[Source] = relationship(back_populates="articles")
    cluster: Mapped["Cluster | None"] = relationship(back_populates="articles")


class Cluster(Base):
    """A de-duplicated *story* — many articles about one event."""
    __tablename__ = "clusters"

    id: Mapped[int] = mapped_column(primary_key=True)
    key: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    category: Mapped[str] = mapped_column(String(32), index=True)
    headline: Mapped[str] = mapped_column(Text)
    first_seen: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    last_seen: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    article_count: Mapped[int] = mapped_column(Integer, default=0)
    source_count: Mapped[int] = mapped_column(Integer, default=0)
    # continuity: yesterday's cluster this one follows on from
    parent_key: Mapped[str | None] = mapped_column(String(64), index=True)

    articles: Mapped[list[Article]] = relationship(back_populates="cluster")
    analysis: Mapped["Analysis | None"] = relationship(back_populates="cluster", uselist=False)


class Analysis(Base):
    __tablename__ = "analyses"

    id: Mapped[int] = mapped_column(primary_key=True)
    cluster_id: Mapped[int] = mapped_column(ForeignKey("clusters.id"), unique=True)
    model: Mapped[str] = mapped_column(String(64))
    prompt_version: Mapped[str] = mapped_column(String(32))
    payload: Mapped[dict] = mapped_column(JSON)          # StoryAnalysis.model_dump()
    democracy_significance: Mapped[float] = mapped_column(Float, default=0.0, index=True)
    democracy_net: Mapped[int] = mapped_column(Integer, default=0)
    impact_scope: Mapped[float] = mapped_column(Float, default=0.0)
    novelty: Mapped[float] = mapped_column(Float, default=0.0)
    credibility: Mapped[float] = mapped_column(Float, default=0.0)
    tokens_in: Mapped[int] = mapped_column(Integer, default=0)
    tokens_out: Mapped[int] = mapped_column(Integer, default=0)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)

    cluster: Mapped[Cluster] = relationship(back_populates="analysis")


class Digest(Base):
    __tablename__ = "digests"

    id: Mapped[int] = mapped_column(primary_key=True)
    digest_date: Mapped[date] = mapped_column(Date, unique=True, index=True)
    generated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    payload: Mapped[dict] = mapped_column(JSON)          # DailyDigest.model_dump(mode="json")
    markdown_path: Mapped[str | None] = mapped_column(String(1000))
    delivered_telegram: Mapped[bool] = mapped_column(Boolean, default=False)
    editorial_note: Mapped[str | None] = mapped_column(Text)

    items: Mapped[list["DigestItemRow"]] = relationship(back_populates="digest",
                                                        cascade="all, delete-orphan")


class DigestItemRow(Base):
    __tablename__ = "digest_items"
    __table_args__ = (UniqueConstraint("digest_id", "category", "rank"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    digest_id: Mapped[int] = mapped_column(ForeignKey("digests.id"))
    cluster_id: Mapped[int] = mapped_column(ForeignKey("clusters.id"))
    category: Mapped[str] = mapped_column(String(32))
    rank: Mapped[int] = mapped_column(Integer)
    score: Mapped[float] = mapped_column(Float)
    score_breakdown: Mapped[dict] = mapped_column(JSON, default=dict)

    digest: Mapped[Digest] = relationship(back_populates="items")


class DeepDiveRow(Base):
    __tablename__ = "deep_dives"

    id: Mapped[int] = mapped_column(primary_key=True)
    digest_id: Mapped[int] = mapped_column(ForeignKey("digests.id"), unique=True)
    cluster_id: Mapped[int] = mapped_column(ForeignKey("clusters.id"))
    model: Mapped[str] = mapped_column(String(64))
    payload: Mapped[dict] = mapped_column(JSON)          # DeepDive.model_dump()
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)


class Feedback(Base):
    """User signal from Telegram/dashboard — feeds the `personal` selection term."""
    __tablename__ = "feedback"

    id: Mapped[int] = mapped_column(primary_key=True)
    cluster_id: Mapped[int | None] = mapped_column(ForeignKey("clusters.id"))
    digest_date: Mapped[date | None] = mapped_column(Date)
    channel: Mapped[str] = mapped_column(String(32), default="telegram")
    signal: Mapped[str] = mapped_column(String(32))       # more | less | deep_dive | irrelevant
    tag: Mapped[str | None] = mapped_column(String(64))   # entity/topic the signal applies to
    note: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)


class LLMCall(Base):
    """Audit trail: every model call, cost and latency. Cheap insurance."""
    __tablename__ = "llm_calls"

    id: Mapped[int] = mapped_column(primary_key=True)
    purpose: Mapped[str] = mapped_column(String(32))      # analysis | deepdive | cluster_title
    model: Mapped[str] = mapped_column(String(64))
    prompt_version: Mapped[str] = mapped_column(String(32), default="v1")
    tokens_in: Mapped[int] = mapped_column(Integer, default=0)
    tokens_out: Mapped[int] = mapped_column(Integer, default=0)
    latency_ms: Mapped[int] = mapped_column(Integer, default=0)
    ok: Mapped[bool] = mapped_column(Boolean, default=True)
    error: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, index=True)

"""Source registry.

Each entry carries editorial metadata (`lean`, `reliability`, `ownership_note`) that is fed to the
analyst prompt as a *prior about framing* — never as a verdict on facts. Bulgarian media ownership
is unusually concentrated, so ownership notes matter more here than in most markets.

Feed URLs are best-effort as of scaffolding time: run `plnews verify-feeds` before trusting them,
and keep `enabled=False` for any feed that fails.
"""
from __future__ import annotations

from app.models.schemas import Category, Lean, Reliability, SourceSpec

C = Category

SOURCES: list[SourceSpec] = [
    # ------------------------------------------------------------------ #
    # Bulgaria
    # ------------------------------------------------------------------ #
    SourceSpec(slug="dnevnik", name="Dnevnik", feed_url="https://www.dnevnik.bg/rss/",
               homepage="https://www.dnevnik.bg", lang="bg", country="BG",
               categories=[C.BG_POLITICS], lean=Lean.CENTER_RIGHT, reliability=Reliability.HIGH,
               ownership_note="Economedia (Ivo Prokopiev). Liberal-reformist editorial line.",
               weight=1.2),
    SourceSpec(slug="capital", name="Capital", feed_url="https://www.capital.bg/rss/",
               homepage="https://www.capital.bg", lang="bg", country="BG",
               categories=[C.BG_POLITICS, C.AI_TECH_BUSINESS], lean=Lean.CENTER_RIGHT,
               reliability=Reliability.HIGH, ownership_note="Economedia. Business/politics weekly.",
               weight=1.2),
    SourceSpec(slug="mediapool", name="Mediapool", feed_url="https://www.mediapool.bg/rss/",
               homepage="https://www.mediapool.bg", lang="bg", country="BG",
               categories=[C.BG_POLITICS], lean=Lean.CENTER, reliability=Reliability.HIGH,
               weight=1.1),
    SourceSpec(slug="svobodnaevropa", name="Svobodna Evropa (RFE/RL Bulgaria)",
               feed_url="https://www.svobodnaevropa.bg/api/zrqiteuuir", lang="bg", country="BG",
               categories=[C.BG_POLITICS], lean=Lean.CENTER, reliability=Reliability.HIGH,
               ownership_note="US-funded public broadcaster; strong investigative desk.", weight=1.2),
    SourceSpec(slug="segabg", name="Sega", feed_url="https://www.segabg.com/rss.xml", lang="bg",
               country="BG", categories=[C.BG_POLITICS], lean=Lean.CENTER_LEFT,
               reliability=Reliability.MEDIUM),
    SourceSpec(slug="offnews", name="OffNews", feed_url="https://offnews.bg/rss", lang="bg",
               country="BG", categories=[C.BG_POLITICS], lean=Lean.CENTER,
               reliability=Reliability.MEDIUM),
    SourceSpec(slug="clubz", name="Club Z", feed_url="https://clubz.bg/rss", lang="bg", country="BG",
               categories=[C.BG_POLITICS], lean=Lean.CENTER, reliability=Reliability.MEDIUM),
    SourceSpec(slug="bta", name="BTA (state news agency)", feed_url="https://www.bta.bg/rss",
               lang="bg", country="BG", categories=[C.BG_POLITICS], lean=Lean.STATE_ALIGNED,
               reliability=Reliability.MEDIUM,
               ownership_note="State agency: reliable for what officials said, weak on scrutiny."),
    SourceSpec(slug="nova", name="Nova TV", feed_url="https://nova.bg/rss", lang="bg", country="BG",
               categories=[C.BG_POLITICS], lean=Lean.CENTER, reliability=Reliability.MEDIUM,
               ownership_note="Ownership has changed hands repeatedly; watch for proprietor interests."),
    SourceSpec(slug="btvnovinite", name="bTV Novinite", feed_url="https://btvnovinite.bg/rss/",
               lang="bg", country="BG", categories=[C.BG_POLITICS], lean=Lean.CENTER,
               reliability=Reliability.MEDIUM),
    SourceSpec(slug="24chasa", name="24 Chasa", feed_url="https://www.24chasa.bg/rss", lang="bg",
               country="BG", categories=[C.BG_POLITICS], lean=Lean.CENTER_RIGHT,
               reliability=Reliability.MEDIUM),
    SourceSpec(slug="trud", name="Trud", feed_url="https://trud.bg/rss/", lang="bg", country="BG",
               categories=[C.BG_POLITICS], lean=Lean.RIGHT, reliability=Reliability.LOW),
    SourceSpec(slug="fakti", name="Fakti.bg", feed_url="https://fakti.bg/rss", lang="bg", country="BG",
               categories=[C.BG_POLITICS], lean=Lean.UNKNOWN, reliability=Reliability.LOW,
               ownership_note="High-volume aggregator; frequently amplifies unverified claims.",
               weight=0.6),
    SourceSpec(slug="toest", name="Toest", feed_url="https://toest.bg/feed/", lang="bg", country="BG",
               categories=[C.BG_POLITICS], lean=Lean.CENTER_LEFT, reliability=Reliability.HIGH,
               ownership_note="Reader-funded; essay/analysis rather than breaking news."),
    SourceSpec(slug="bird", name="Bird.bg", feed_url="https://bird.bg/feed/", lang="bg", country="BG",
               categories=[C.BG_POLITICS], lean=Lean.CENTER, reliability=Reliability.HIGH,
               ownership_note="Investigative outlet focused on corruption and procurement."),

    # ------------------------------------------------------------------ #
    # Global politics
    # ------------------------------------------------------------------ #
    SourceSpec(slug="reuters_world", name="Reuters World",
               feed_url="https://www.reutersagency.com/feed/?best-topics=political-general&post_type=best",
               categories=[C.GLOBAL_POLITICS], lean=Lean.CENTER, reliability=Reliability.HIGH, weight=1.3),
    SourceSpec(slug="apnews", name="AP News", feed_url="https://rsshub.app/apnews/topics/politics",
               categories=[C.GLOBAL_POLITICS], lean=Lean.CENTER, reliability=Reliability.HIGH, weight=1.3),
    SourceSpec(slug="bbc_world", name="BBC World",
               feed_url="https://feeds.bbci.co.uk/news/world/rss.xml",
               categories=[C.GLOBAL_POLITICS], lean=Lean.CENTER, reliability=Reliability.HIGH, weight=1.2),
    SourceSpec(slug="guardian_world", name="The Guardian World",
               feed_url="https://www.theguardian.com/world/rss",
               categories=[C.GLOBAL_POLITICS], lean=Lean.CENTER_LEFT, reliability=Reliability.HIGH),
    SourceSpec(slug="politico_eu", name="Politico Europe", feed_url="https://www.politico.eu/feed/",
               categories=[C.GLOBAL_POLITICS], lean=Lean.CENTER, reliability=Reliability.HIGH, weight=1.2),
    SourceSpec(slug="euobserver", name="EUobserver", feed_url="https://euobserver.com/rss.xml",
               categories=[C.GLOBAL_POLITICS], lean=Lean.CENTER, reliability=Reliability.HIGH),
    SourceSpec(slug="euractiv", name="Euractiv", feed_url="https://www.euractiv.com/feed/",
               categories=[C.GLOBAL_POLITICS], lean=Lean.CENTER, reliability=Reliability.MEDIUM),
    SourceSpec(slug="dw_europe", name="Deutsche Welle", feed_url="https://rss.dw.com/rdf/rss-en-eu",
               categories=[C.GLOBAL_POLITICS], lean=Lean.CENTER, reliability=Reliability.HIGH),
    SourceSpec(slug="aljazeera", name="Al Jazeera", feed_url="https://www.aljazeera.com/xml/rss/all.xml",
               categories=[C.GLOBAL_POLITICS], lean=Lean.CENTER_LEFT, reliability=Reliability.MEDIUM),
    SourceSpec(slug="balkaninsight", name="Balkan Insight (BIRN)",
               feed_url="https://balkaninsight.com/feed/", categories=[C.GLOBAL_POLITICS, C.BG_POLITICS],
               lean=Lean.CENTER, reliability=Reliability.HIGH,
               ownership_note="Regional investigative network; strong on rule-of-law backsliding.",
               weight=1.2),

    # ------------------------------------------------------------------ #
    # AI / tech / business
    # ------------------------------------------------------------------ #
    SourceSpec(slug="arstechnica", name="Ars Technica",
               feed_url="https://feeds.arstechnica.com/arstechnica/index",
               categories=[C.AI_TECH_BUSINESS], lean=Lean.CENTER, reliability=Reliability.HIGH, weight=1.1),
    SourceSpec(slug="techcrunch", name="TechCrunch", feed_url="https://techcrunch.com/feed/",
               categories=[C.AI_TECH_BUSINESS], lean=Lean.CENTER, reliability=Reliability.MEDIUM,
               ownership_note="Heavy funding-announcement volume; discount PR-driven items.", weight=0.9),
    SourceSpec(slug="theverge", name="The Verge", feed_url="https://www.theverge.com/rss/index.xml",
               categories=[C.AI_TECH_BUSINESS], lean=Lean.CENTER_LEFT, reliability=Reliability.MEDIUM),
    SourceSpec(slug="mit_tr", name="MIT Technology Review",
               feed_url="https://www.technologyreview.com/feed/",
               categories=[C.AI_TECH_BUSINESS], lean=Lean.CENTER, reliability=Reliability.HIGH, weight=1.1),
    SourceSpec(slug="ft_tech", name="Financial Times (Tech)",
               feed_url="https://www.ft.com/technology?format=rss",
               categories=[C.AI_TECH_BUSINESS], lean=Lean.CENTER_RIGHT, reliability=Reliability.HIGH,
               ownership_note="Paywalled: expect headline+summary only.", weight=1.1),
    SourceSpec(slug="hn_frontpage", name="Hacker News (front page)",
               feed_url="https://hnrss.org/frontpage?points=250",
               categories=[C.AI_TECH_BUSINESS], lean=Lean.UNKNOWN, reliability=Reliability.MEDIUM,
               ownership_note="Signal for what the industry is discussing, not a reporting source.",
               weight=0.8),
    SourceSpec(slug="stanford_hai", name="Stanford HAI", feed_url="https://hai.stanford.edu/news/rss.xml",
               categories=[C.AI_TECH_BUSINESS], lean=Lean.CENTER, reliability=Reliability.HIGH),
]

BY_SLUG: dict[str, SourceSpec] = {s.slug: s for s in SOURCES}

# Credibility multiplier applied during scoring.
RELIABILITY_WEIGHT: dict[Reliability, float] = {
    Reliability.HIGH: 1.0,
    Reliability.MEDIUM: 0.75,
    Reliability.LOW: 0.45,
    Reliability.PROPAGANDA: 0.15,
}


def sources_for(category: Category) -> list[SourceSpec]:
    return [s for s in SOURCES if s.enabled and category in s.categories]


def sync_sources_to_db(session) -> int:
    """Upsert the registry into the `sources` table. Idempotent."""
    from app.models.orm import Source

    n = 0
    for spec in SOURCES:
        row = session.query(Source).filter_by(slug=spec.slug).one_or_none()
        if row is None:
            row = Source(slug=spec.slug)
            session.add(row)
            n += 1
        row.name = spec.name
        row.feed_url = str(spec.feed_url)
        row.homepage = str(spec.homepage) if spec.homepage else None
        row.lang = spec.lang
        row.country = spec.country
        row.categories = [c.value for c in spec.categories]
        row.lean = spec.lean.value
        row.reliability = spec.reliability.value
        row.ownership_note = spec.ownership_note
        row.weight = spec.weight
        row.enabled = spec.enabled
    session.flush()
    return n

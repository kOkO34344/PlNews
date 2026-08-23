from datetime import date, datetime, timezone

from app.delivery import formatting as fmt
from app.digest.markdown import render_digest_markdown
from app.models.schemas import Category, DailyDigest, DigestItem, SelectionScore
from tests.factories import make_analysis, make_cluster, make_deep_dive


def _digest() -> DailyDigest:
    items = []
    for cat in (Category.BG_POLITICS, Category.GLOBAL_POLITICS, Category.AI_TECH_BUSINESS):
        for rank in (1, 2, 3):
            key = f"{cat.value}-{rank}"
            items.append(DigestItem(
                rank=rank, category=cat, analysis=make_analysis(key, cat),
                score=SelectionScore(cluster_key=key, total=0.7, democracy=0.6, impact=0.6,
                                     novelty=0.7, credibility=0.8, personal=0.5,
                                     explanation="democracy 0.60 · credibility 0.80"),
                refs=make_cluster(key, cat).articles,
            ))
    return DailyDigest(
        digest_date=date(2026, 8, 23),
        generated_at=datetime(2026, 8, 23, 6, 0, tzinfo=timezone.utc),
        items=items,
        deep_dive=make_deep_dive("bg_politics-1"),
        deep_dive_refs=make_cluster().articles,
        stats={"fetched": 240, "clusters": 31, "sources": 30, "net_direction": -0.4,
               "democracy_relevant": 7},
        editorial_note="A day dominated by judicial procedure.",
    )


def test_markdown_has_frontmatter_and_all_sections():
    md = render_digest_markdown(_digest())
    assert md.startswith("---\n")
    assert "type: news-digest" in md
    assert "🇧🇬 Bulgarian politics" in md
    assert "🌍 Global politics" in md
    assert "🤖 AI · tech · business" in md
    assert "Deep dive" in md
    assert "[[National Assembly]]" in md          # entity wiki-links
    assert "> [!warning]" in md or "> [!note]" in md


def test_telegram_messages_stay_under_limit():
    msgs = fmt.build_messages(_digest(), compact=False, include_deep_dive=True)
    assert msgs, "expected at least one message"
    assert all(len(m) <= 4096 for m in msgs)
    assert "3-3-3 Digest" in msgs[0]


def test_telegram_escapes_html():
    assert fmt.esc("<script>&") == "&lt;script&gt;&amp;"

"""Cross-lingual clustering, pinned to the real failure from 2026-08-23.

That day one Zelensky statement produced three clusters — five English reports, and two
separate Bulgarian ones — and took two of the three global-politics slots in the digest.
Two distinct bugs caused it: greedy clustering compared each candidate only against a
group's seed, and nothing compared across scripts at all.
"""
from app.ingestion.dedupe import cluster_articles, merge_multilingual
from app.ingestion.translit import cross_lingual_similarity, signature, transliterate
from app.models.schemas import Category
from tests.factories import make_article, make_cluster, make_ref

EN = [
    "Holding election in wartime would risk destroying Ukraine, says Zelenskyy",
    "Wartime elections would 'destroy' Ukraine, says Zelensky",
    "Zelenskyy: Elections would 'tear Ukraine apart'",
]
BG = [
    "Зеленски смята, че избори по време на война са огромен риск за Украйна",
    "Зеленски: Изборите са цунами, което ще раздели Украйна",
    "Военновременни избори биха били „цунами“, което би разделило Украйна, заяви Зеленски",
]
OTHER_ZELENSKY = [
    "Zelensky should be asked what he knew about government corruption, sacked minister tells BBC",
    "Rescuers dig through Ukraine mall wreckage as Zelensky condemns 'despicable' Russian strike",
]


def test_transliteration_romanises_bulgarian():
    assert transliterate("Зеленски") == "zelenski"
    assert transliterate("Щастие") == "shtastie"


def test_signature_lands_both_languages_on_the_same_words():
    en = signature("Zelenskyy: Elections would tear Ukraine apart")
    bg = signature("Зеленски: Изборите са цунами, което ще раздели Украйна")
    for word in ("zelensk", "election", "ukraine"):
        assert word in en and word in bg, f"{word!r} missing from one signature"


def test_same_story_scores_above_different_story_across_languages():
    same = min(cross_lingual_similarity(e, b) for e in EN for b in BG)
    different = max(cross_lingual_similarity(e, o) for e in EN for o in OTHER_ZELENSKY)
    assert same > different, "cross-lingual matches must outrank same-language non-matches"
    assert same >= 0.16 > different, f"threshold 0.16 must sit in the gap ({different:.3f}, {same:.3f})"


def test_single_linkage_keeps_a_chain_together():
    """A matches B and B matches C, but A does not match C.

    Comparing only against a group's seed drops C. Real stories fragment this way as
    they get re-reported and the wording drifts. (Note: this is *not* what split the two
    Bulgarian Zelensky clusters — inflection defeated TF-IDF there, and the cross-lingual
    pass below is what recovers those.)
    """
    # Containment: A-B 0.71, B-C 0.67, A-C 0.00 — a chain, not a clique.
    articles = [
        make_article("dnevnik", "Parliament approves judicial reform package on second reading",
                     url="https://x/1"),
        make_article("mediapool", "Parliament approves judicial reform package after heated debate",
                     url="https://x/2"),
        make_article("segabg", "Heated debate as MPs back the reform package", url="https://x/3"),
    ]
    clusters = cluster_articles(articles, Category.BG_POLITICS)
    assert len(clusters) == 1, [c.headline for c in clusters]


def test_merge_multilingual_collapses_the_three_zelensky_clusters():
    def cluster_of(key, titles, slug, name):
        refs = [make_ref(slug, name, title=t) for t in titles]
        for i, r in enumerate(refs):
            r.url = f"https://{slug}/{key}/{i}"
        c = make_cluster(key, Category.GLOBAL_POLITICS, refs=refs)
        return c.model_copy(update={"headline": titles[0]})

    clusters = [
        cluster_of("en", EN, "bbc_world", "BBC"),
        cluster_of("bg1", BG[:2], "dnevnik", "Dnevnik"),
        cluster_of("bg2", BG[2:], "mediapool", "Mediapool"),
        cluster_of("other", OTHER_ZELENSKY[:1], "guardian_world", "Guardian"),
    ]
    merged = merge_multilingual(clusters)

    assert len(merged) == 2, [c.headline for c in merged]
    biggest = max(merged, key=lambda c: len(c.articles))
    assert len(biggest.articles) == 6, "all three Zelensky-election clusters should be one"
    # The unrelated corruption story must survive on its own.
    assert any("corruption" in c.headline for c in merged)


def test_merge_is_a_no_op_on_unrelated_stories():
    def solo(key, title, slug):
        refs = [make_ref(slug, slug.title(), title=title)]
        refs[0].url = f"https://{slug}/{key}"
        return make_cluster(key, Category.GLOBAL_POLITICS, refs=refs).model_copy(
            update={"headline": title})

    clusters = [
        solo("a", "Trump imposes 50% tariffs after US-Canada trade talks collapse", "bbc_world"),
        solo("b", "Зеленски: Изборите са цунами, което ще раздели Украйна", "dnevnik"),
        solo("c", "Waymo details custom 5nm chip as robotaxi rollout continues", "theverge"),
    ]
    assert len(merge_multilingual(clusters)) == 3

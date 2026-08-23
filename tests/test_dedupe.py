from app.ingestion.dedupe import cluster_articles, drop_near_duplicates, hamming, normalize, simhash
from app.models.schemas import Category
from tests.factories import make_article


def test_normalize_strips_stopwords_and_punctuation():
    assert normalize("The Parliament, in Sofia!") == "parliament sofia"


def test_simhash_is_stable_and_close_for_similar_text():
    a = simhash("Parliament votes on judicial reform amendments")
    b = simhash("Parliament votes on judicial reform amendment")
    c = simhash("Nvidia announces new data centre chip")
    assert hamming(a, b) < hamming(a, c)


def test_drop_near_duplicates_keeps_one_per_source():
    articles = [
        make_article("dnevnik", "Parliament votes on judicial reform", url="https://a/1"),
        make_article("dnevnik", "Parliament votes on judicial reform", url="https://a/2"),
        make_article("mediapool", "Parliament votes on judicial reform", url="https://b/1"),
    ]
    kept = drop_near_duplicates(articles)
    assert len(kept) == 2  # cross-source coverage survives; same-source copy does not


def test_cluster_articles_groups_same_event():
    articles = [
        make_article("dnevnik", "Parliament passes judicial reform on second reading"),
        make_article("mediapool", "MPs pass judicial reform amendments on second reading"),
        make_article("capital", "Nvidia unveils new data centre accelerator"),
    ]
    clusters = cluster_articles(articles, Category.BG_POLITICS)
    sizes = sorted(len(c.articles) for c in clusters)
    assert sizes == [1, 2]

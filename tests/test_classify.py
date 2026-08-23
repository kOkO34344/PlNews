"""Regression tests built from a real ingestion run on 2026-08-23.

Every case below is an actual headline the first version of the classifier got wrong.
"""
from app.ingestion.classify import classify, is_noise
from app.models.schemas import Category
from tests.factories import make_article


def _c(title: str, slug: str = "dnevnik", summary: str = "") -> Category | None:
    a = make_article(slug, title)
    return classify(a.model_copy(update={"summary": summary}))


def test_bulgarian_source_foreign_story_is_not_bg_politics():
    # Bulgarian-language coverage of a foreign event must not become domestic politics.
    assert _c("Повечето германци очакват смяна на Мерц преди следващите избори") is Category.GLOBAL_POLITICS
    assert _c("Русия атакува с дронове влак с близо 600 пътници край Одеса") is Category.GLOBAL_POLITICS


def test_domestic_political_story_is_bg_politics():
    assert _c("Андрей Гюров има подкрепата на десните, заяви Радан Кънев",
              summary="Изборът на подуправител на БНБ разделя парламента в София") is Category.BG_POLITICS
    assert _c('"Прогресивна България" очаква нов Висш съдебен съвет до ноември') is Category.BG_POLITICS


def test_non_political_domestic_news_is_dropped():
    assert _c("Дерайлирал влак спря движението между Владая и Горна баня") is None
    assert _c("Нивото на река Дунав се повиши леко") is None


def test_science_is_not_tech_business():
    assert _c("Volcanoes that made history", "arstechnica") is None
    assert _c("Robot horse and rider steal the spotlight at Chinese conference", "theverge") \
        is Category.AI_TECH_BUSINESS  # robots do count


def test_sport_is_filtered():
    # The noise list is the fast path...
    assert is_noise(make_article("bbc_world", "Sydney Marathon laughs off medal error"))
    assert not is_noise(make_article("bbc_world", "Zelenskyy: Elections would 'tear Ukraine apart'"))
    # ...and the signal gate catches what the word list misses (unbounded athlete names).
    assert _c("'New season, new trim' - Haaland reveals buzzcut", "bbc_world") is None


def test_tech_story_from_a_politics_source_routes_to_tech():
    assert _c("ЕС приема AI Act — какво означава за българските компании",
              summary="Регулацията на изкуствения интелект и данните") is Category.AI_TECH_BUSINESS


def test_tech_policy_keeps_its_political_edge():
    assert _c("Is it legal to train AI models on copyrighted books? It's complicated",
              "techcrunch") is Category.AI_TECH_BUSINESS
    assert _c("Flock CEO calls for compromise as surveillance company faces growing backlash",
              "techcrunch") is Category.AI_TECH_BUSINESS


def test_bulgarian_language_is_the_domestic_prior():
    # No BG_MARKERS keyword in this headline, but it is Bulgarian and names no foreign
    # actor — so it is domestic politics.
    assert _c("Андрей Гюров има подкрепата на десните, заяви Радан Кънев") is Category.BG_POLITICS
    # Same source, same language, but a foreign actor is named.
    assert _c("Путин: Русия няма да се примири с решението") is Category.GLOBAL_POLITICS


def test_weather_warnings_are_noise():
    assert is_noise(make_article("dnevnik", "Жълт код за опасни жеги в почти цялата страна"))


def test_publisher_url_section_is_the_strongest_noise_signal():
    # No keyword list contains every athlete's surname; the section path does the work.
    haaland = make_article("bbc_world", "'New season, new trim' - Haaland reveals buzzcut")
    assert is_noise(haaland.model_copy(
        update={"url": "https://www.bbc.co.uk/sport/football/articles/c8xk2"}))
    # ...and it must not swallow politics that merely mentions a section-like word.
    assert not is_noise(make_article("bbc_world", "Court blocks emergency powers extension")
                        .model_copy(update={"url": "https://www.bbc.co.uk/news/world-europe-123"}))

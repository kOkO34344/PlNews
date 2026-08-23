"""Category routing and noise filtering.

Runs before the LLM so we never pay tokens to discover an article is off-topic.

Three signals decide where an article goes:
  * POLITICS_SIGNAL      — is anything institutional at stake at all?
  * TECH_BUSINESS_SIGNAL — is this about technology, AI or markets?
  * BG_MARKERS           — Bulgarian actors, institutions, places.

The source's own categories are only a tie-break. An earlier version trusted them
outright, which sent every Bulgarian-language story about a Japanese earthquake into
`bg_politics` simply because Dnevnik is a Bulgarian-politics source. Content wins;
the source only breaks ties.
"""
from __future__ import annotations

import re
from functools import lru_cache

from app.ingestion.sources import BY_SLUG
from app.models.schemas import ArticleIn, Category

# --------------------------------------------------------------------------- #
# Vocabularies. Lowercase, substring-matched, Bulgarian and English together.
# --------------------------------------------------------------------------- #
POLITICS_CORE: tuple[str, ...] = (
    # institutions & process
    "парламент", "народното събрание", "министер", "правителств", "кабинет", "депутат",
    "президент", "вицепрезидент", "съд", "прокур", "конституц", "закон", "законопроект",
    "изборите", "избори", "вот", "коалиц", "оставк", "импийчмънт", "бюджет", "данък",
    "корупц", "разследван", "санкци", "референдум", "партия", "опозиц", "мандат",
    "евродепутат", "еврокомис", "европейски съюз", "нато", "мвр", "днсk", "кпк", "антикорупц",
    "висш съдебен съвет", "омбудсман", "мониторинг", "правова държава", "медиен плурализъм",
    "протест", "митинг", "стачка", "цензур", "журналист",
    "политик", "политическ", "десни", "десница", "левица", "кандидат", "избирател",
    "мнозинство", "председател", "лидер на", "управляващ", "реформ",
    "parliament", "minister", "government", "cabinet", "president", "chancellor", "premier",
    "court", "judge", "judicial", "prosecut", "constitution", "legislation", "law ", "bill ",
    "election", "referendum", "coalition", "resign", "impeach", "budget", "tax ", "sanction",
    "corruption", "investigation", "treaty", "diplomat", "summit", "sovereignt", "regulator",
    "eu ", "european commission", "european parliament", "nato", "united nations", "council of europe",
    "protest", "strike", "censor", "press freedom", "journalist", "rule of law", "democracy",
    "authoritarian", "coup", "ceasefire", "war ", "military aid", "occupation", "annex",
)

# Foreign actors, places and conflict vocabulary. Doubles as the "is this story about
# somewhere else?" test, which is how a Bulgarian-language wire piece about Odesa avoids
# being filed as domestic politics.
FOREIGN_MARKERS: tuple[str, ...] = (
    "русия", "руск", "украйна", "украинск", "путин", "зеленски", "москва", "киев", "одеса",
    "харков", "харкив", "обстрел", "дрон", "войната", "сащ", "тръмп", "китай", "китайск",
    "израел", "израелск", "газа", "хамас", "иран", "ирански", "турция", "ердоган", "сирия",
    "герман", "френск", "франция", "полша", "полск", "унгар", "орбан", "сърбия", "сръбск",
    "гърция", "румъния", "австрия", "италия", "испания", "британия", "лондон", "вашингтон",
    "нато", "оон", "брюксел", "молдова", "грузия", "беларус", "северна корея", "венецуела",
    "russia", "ukraine", "putin", "zelensk", "kremlin", "moscow", "kyiv", "odesa", "kharkiv",
    "drone strike", "airstrike", "shelling", "troops", "trump", "china", "beijing", "israel",
    "gaza", "iran", "hamas", "hezbollah", "taiwan", "north korea", "venezuela", "serbia",
    "hungary", "orban", "georgia", "moldova", "belarus", "brussels", "washington", "pentagon",
    "germany", "france", "poland", "romania", "greece", "turkey", "erdogan", "india", "pakistan",
)

POLITICS_SIGNAL: tuple[str, ...] = POLITICS_CORE + FOREIGN_MARKERS

TECH_BUSINESS_SIGNAL: tuple[str, ...] = (
    "изкуствен интелект", "технолог", "стартъп", "чип", "полупроводник", "данни", "киберат",
    "софтуер", "платформ", "инвестиц", "придобиване", "борса", "акции",
    "ai ", " ai", "artificial intelligence", "machine learning", "llm", "chatbot", "model ",
    "openai", "anthropic", "deepmind", "nvidia", "microsoft", "google", "meta ", "apple",
    "amazon", "tesla", "semiconductor", "chip", "compute", "data centre", "data center",
    "cloud", "software", "algorithm", "startup", "venture", "funding round", "ipo",
    "acquisition", "merger", "antitrust", "monopoly", "market cap", "earnings", "revenue",
    "crypto", "blockchain", "cyberattack", "data breach", "encryption", "privacy", "gdpr",
    "ai act", "content moderation", "platform", "robot", "autonomous", "quantum",
    "ceo", "chief executive", "shareholder", "layoff", "valuation", "surveillance",
    "facial recognition", "spyware", "open source", "gpu", "silicon", "smartphone", "app store",
    "subscription", "licensing", "copyright", "patent", "training data",
)

BG_MARKERS: tuple[str, ...] = (
    "българия", "български", "българск", "софия", "пловдив", "варна", "бургас", "русе",
    "народното събрание", "герб", "пп-дб", "продължаваме промяната", "демократична българия",
    "възраждане", "дпс", "бсп", "итн", "мech", "борисов", "пеевски", "радев", "желязков",
    "главния прокурор", "вss", "цик", "нои", "бнб", "нап",
    "bulgaria", "bulgarian", "sofia", "gerb", "peevski", "borissov", "radev", "schengen",
    "eurozone", "еврозона", "шенген",
)

# Hard drops: nothing here belongs in a democracy-focused digest, whatever the source.
NOISE: tuple[str, ...] = (
    # sport
    "хороскоп", "футбол", "цска", "левски", "лудогорец", "тенис", "олимп", "мач", "гол ",
    "шампион", "тото", "формула 1",
    "football", "soccer", "premier league", "champions league", "world cup", "cricket", "rugby",
    "tennis", "olympic", "marathon", "nba", "nfl", "f1 ", "grand prix", "transfer window",
    "goalkeeper", "striker", "coach", "match ", " vs ", "medal",
    # weather, accidents, crime blotter, celebrity, service journalism
    "времето", "прогноза за времето", "хороскопа", "земетресение", "наводнение", "пожар край",
    "катастрофа", "дерайлира", "загина при", "ранен при", "изчезна", "убийство", "обир",
    "първенство", "волейбол", "баскетбол", "хандбал", "националният отбор",
    "жълт код", "оранжев код", "червен код", "жеги", "гръмотевич", "снеговалеж",
    "weather forecast", "earthquake", "flooding", "wildfire", "car crash", "derail",
    "heatwave warning", "storm warning",
    "horoscope", "recipe", "deals of the day", "best deals", "sponsored", "advertorial",
    "coupon", "black friday", "gift guide", "review: ", "hands-on", "how to watch",
    "celebrity", "royal family", "obituary", "died aged", "box office",
)

MIN_SIGNAL = 1          # a story must show at least this much of *something*
CROSS_CATEGORY_MIN = 2  # signal needed to override the source's declared categories


# Naive substring matching is wrong for Bulgarian: "вот" (vote) hides inside "нивото"
# (the level of), so a river-level report scored as political news. Terms are matched at a
# word boundary instead. Longer terms match as prefixes, which is what Slavic inflection
# needs ("парламент" → "парламентът"); short terms must match whole words.
EXACT_MAX_LEN = 4


@lru_cache(maxsize=None)
def _matcher(terms: tuple[str, ...]) -> re.Pattern[str]:
    cleaned = {t.strip().lower() for t in terms if t.strip()}
    exact = [re.escape(t) for t in cleaned if len(t) <= EXACT_MAX_LEN]
    prefix = [re.escape(t) for t in cleaned if len(t) > EXACT_MAX_LEN]
    parts = []
    if exact:
        parts.append(r"(?:" + "|".join(sorted(exact, key=len, reverse=True)) + r")(?!\w)")
    if prefix:
        parts.append(r"(?:" + "|".join(sorted(prefix, key=len, reverse=True)) + r")")
    return re.compile(r"(?<!\w)(?:" + "|".join(parts) + r")", re.UNICODE)


def _score(text: str, terms: tuple[str, ...]) -> int:
    """Number of *distinct* vocabulary hits — repetition should not inflate a score."""
    return len(set(_matcher(terms).findall(text)))


def _haystack(article: ArticleIn) -> str:
    return " ".join(
        filter(None, [article.title, article.summary or "", (article.body or "")[:1500]])
    ).lower()


def is_noise(article: ArticleIn) -> bool:
    """Sport, weather, accidents, celebrity and service journalism.

    Applied to the title only: a passing mention of 'earthquake' deep in a political
    story should not disqualify it.
    """
    return bool(_matcher(NOISE).search((article.title or "").lower()))


def classify(article: ArticleIn) -> Category | None:
    """Best category, or None if the article does not belong in the digest."""
    text = _haystack(article)
    spec = BY_SLUG.get(article.source_slug)
    allowed = set(spec.categories) if spec else set(Category)

    civic = _score(text, POLITICS_CORE)
    foreign_only = _score(text, FOREIGN_MARKERS)
    # A place name on its own is not a political signal — "dead fish in a Polish canal"
    # is not global politics. Require civic vocabulary, or two independent foreign markers.
    politics = civic + foreign_only if (civic or foreign_only >= CROSS_CATEGORY_MIN) else 0
    tech = _score(text, TECH_BUSINESS_SIGNAL)
    bg = _score(text, BG_MARKERS)
    foreign = foreign_only
    politics_source = bool(allowed & {Category.BG_POLITICS, Category.GLOBAL_POLITICS})

    if politics < MIN_SIGNAL and tech < MIN_SIGNAL:
        return None  # a train derailment is news, but it is not this digest's news

    # Tech/business wins when it clearly dominates — including from a politics source,
    # which is how "EU AI Act" coverage in Dnevnik reaches the right bucket.
    if tech > politics:
        if Category.AI_TECH_BUSINESS in allowed or tech >= CROSS_CATEGORY_MIN:
            return Category.AI_TECH_BUSINESS

    if politics >= MIN_SIGNAL:
        # Domestic vs foreign is decided by the text, not by where the outlet is based.
        # Language is the strongest available prior: a Bulgarian-language political story
        # that names no foreign actor is almost always domestic, even when the headline
        # happens to contain no keyword from BG_MARKERS.
        domestic = bg >= MIN_SIGNAL or (article.lang == "bg" and foreign == 0)
        if domestic and (Category.BG_POLITICS in allowed or bg >= CROSS_CATEGORY_MIN):
            return Category.BG_POLITICS
        if (Category.GLOBAL_POLITICS in allowed or politics_source
                or politics >= CROSS_CATEGORY_MIN):
            return Category.GLOBAL_POLITICS

    if tech >= MIN_SIGNAL and (Category.AI_TECH_BUSINESS in allowed or tech >= CROSS_CATEGORY_MIN):
        return Category.AI_TECH_BUSINESS

    return None

"""Cross-lingual matching for story clustering.

TF-IDF cannot tell that "Зеленски: Изборите са цунами, което ще раздели Украйна" and
"Zelenskyy: Elections would 'tear Ukraine apart'" are the same story, so a Bulgarian
and an English report of one event become two clusters and waste a digest slot.

Rather than pull in a multilingual embedding model (a ~500MB dependency for what is,
here, a vocabulary problem), this maps both languages onto one comparison string:

  1. a domain lexicon rewrites the political vocabulary the digest actually deals in,
  2. everything else is transliterated from Cyrillic to Latin,
  3. similarity is character 4-gram Jaccard, which absorbs the inflection and
     transliteration drift that exact token matching cannot ("зеленски" → "zelenski"
     vs "zelenskyy", "украйна" → "ukrayna" vs "ukraine").

The lexicon is deliberately small and specific to this digest's subject matter. It does
not need to be a translation system; it needs to make the fifty words that carry a
political headline line up.
"""
from __future__ import annotations

import re
import unicodedata

# BGN/PCGN-style romanisation, which is what Bulgarian names use in English copy.
CYRILLIC: dict[str, str] = {
    "а": "a", "б": "b", "в": "v", "г": "g", "д": "d", "е": "e", "ж": "zh", "з": "z",
    "и": "i", "й": "y", "к": "k", "л": "l", "м": "m", "н": "n", "о": "o", "п": "p",
    "р": "r", "с": "s", "т": "t", "у": "u", "ф": "f", "х": "h", "ц": "ts", "ч": "ch",
    "ш": "sh", "щ": "sht", "ъ": "a", "ь": "y", "ю": "yu", "я": "ya",
    # Russian/Ukrainian letters that show up in quoted names
    "ы": "y", "э": "e", "ё": "yo", "і": "i", "ї": "yi", "є": "ye", "ґ": "g",
}

# Bulgarian → English for the vocabulary this digest runs on. Keys are matched as word
# prefixes, so one entry covers the inflected forms ("избори", "изборите", "изборна").
LEXICON: dict[str, str] = {
    # process and institutions
    "избор": "election", "гласув": "vote", "референдум": "referendum",
    "парламент": "parliament", "депутат": "mp", "правителств": "government",
    "министър": "minister", "министерств": "ministry", "президент": "president",
    "премиер": "premier", "кабинет": "cabinet", "коалиц": "coalition",
    "опозиц": "opposition", "партия": "party", "мандат": "mandate",
    "оставк": "resignation", "вот на недоверие": "no confidence vote",
    "съд": "court", "прокур": "prosecutor", "закон": "law", "конституц": "constitution",
    "разследван": "investigation", "корупц": "corruption", "санкци": "sanction",
    "бюджет": "budget", "данък": "tax", "мит": "tariff", "преговор": "talks",
    "споразумен": "agreement", "договор": "treaty", "протест": "protest",
    "стачк": "strike", "цензур": "censorship", "журналист": "journalist",
    "разделянe": "split", "раздели": "split", "разделило": "split",
    # conflict
    "война": "war", "военн": "war", "примирие": "ceasefire", "удар": "strike",
    "обстрел": "shelling", "дрон": "drone", "ракет": "missile", "войск": "troops",
    "мобилизац": "mobilisation", "окупац": "occupation", "бежан": "refugee",
    "жертв": "casualty", "убит": "killed", "ранен": "wounded",
    # places and actors that do not transliterate onto their English spelling
    "украйна": "ukraine", "украин": "ukraine", "русия": "russia", "руск": "russia",
    "москва": "moscow", "киев": "kyiv", "одеса": "odesa", "харков": "kharkiv",
    "българия": "bulgaria", "българск": "bulgaria", "софия": "sofia",
    "сащ": "usa", "американск": "usa", "вашингтон": "washington",
    "герман": "germany", "франция": "france", "френск": "france",
    "полша": "poland", "полск": "poland", "унгар": "hungary", "сърбия": "serbia",
    "гърция": "greece", "румъния": "romania", "турция": "turkey",
    "китай": "china", "китайск": "china", "израел": "israel", "иран": "iran",
    "европейск": "european", "еврокомис": "european commission", "брюксел": "brussels",
    "обединеното кралство": "uk", "великобритания": "uk",
    # people whose romanisation differs from the BGN transliteration
    "зеленски": "zelensky", "путин": "putin", "тръмп": "trump", "орбан": "orban",
    "ердоган": "erdogan", "макрон": "macron", "мерц": "merz",
}

_PUNCT = re.compile(r"[^\w\s]", re.UNICODE)
_SPACE = re.compile(r"\s+")

STOPWORDS = {
    # English
    "the", "a", "an", "of", "in", "on", "for", "to", "and", "with", "at", "by", "from",
    "as", "is", "are", "was", "were", "said", "says", "after", "over", "new", "would",
    "could", "that", "this", "his", "her", "its", "it", "be", "been", "has", "have",
    # Bulgarian, already romanised at the point of filtering
    "i", "v", "na", "za", "s", "ot", "po", "che", "se", "da", "e", "sa", "ne", "no",
    "kato", "sled", "koeto", "koyto", "shte", "bi", "biha", "bili", "tova", "tozi",
    "si", "mu", "im", "smyata", "zayavi", "kaza",
}


def transliterate(text: str) -> str:
    out: list[str] = []
    for ch in text.lower():
        out.append(CYRILLIC.get(ch, ch))
    return "".join(out)


def apply_lexicon(text: str) -> str:
    """Rewrite known Bulgarian terms into their English equivalents, longest first so
    that "военновременни" is not shadowed by a shorter prefix."""
    lowered = text.lower()
    for term in sorted(LEXICON, key=len, reverse=True):
        if term in lowered:
            lowered = lowered.replace(term, f" {LEXICON[term]} ")
    return lowered


def signature(text: str) -> str:
    """One comparable string, whatever language the headline was written in."""
    s = unicodedata.normalize("NFKC", text or "")
    s = apply_lexicon(s)
    s = transliterate(s)
    s = _PUNCT.sub(" ", s)
    tokens = [t for t in _SPACE.split(s) if t and t not in STOPWORDS and len(t) > 2]
    return " ".join(tokens)


def char_ngrams(text: str, n: int = 4) -> set[str]:
    packed = text.replace(" ", "")
    if len(packed) < n:
        return {packed} if packed else set()
    return {packed[i : i + n] for i in range(len(packed) - n + 1)}


def cross_lingual_similarity(a: str, b: str) -> float:
    """Jaccard over character 4-grams of the two signatures, 0.0-1.0."""
    ga, gb = char_ngrams(signature(a)), char_ngrams(signature(b))
    if not ga or not gb:
        return 0.0
    return len(ga & gb) / len(ga | gb)

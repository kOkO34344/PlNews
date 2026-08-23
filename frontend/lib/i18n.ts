/**
 * Interface language. Two locales, one dictionary, no framework.
 *
 * The analysis prose is a separate problem: it is written in English by the analyst
 * prompt and is translated server-side (see `plnews translate`), arriving on the digest
 * as `translations.bg`. This file covers only the chrome — labels, section names, the
 * democracy rubric's own vocabulary — which is finite and belongs in the repo.
 *
 * Bulgarian terminology follows the usage in Bulgarian constitutional and press-freedom
 * writing rather than literal translation: "спирачки и противотежести" for checks and
 * balances, "върховенство на правото" for rule of law.
 */

export type Locale = "en" | "bg";

export const LOCALES: { code: Locale; label: string; short: string }[] = [
  { code: "en", label: "English", short: "EN" },
  { code: "bg", label: "Български", short: "БГ" },
];

type Dict = Record<string, string>;

const en: Dict = {
  "masthead.place": "Sofia",
  "masthead.keys": "j / k to move · o to open",
  "masthead.moved": "The institutions moved",
  "masthead.suffix": " today.",
  "masthead.fallbackNote": "Nine stories, {n} of them with something institutional at stake.",
  "banner.sample": "Sample data. The API returned no digest — run {cmd} to fill this in.",
  "banner.untranslated": "This digest has not been translated yet. Run {cmd} for Bulgarian.",

  "trace.label": "{n}-day trace · scale ±{peak}",
  "trace.caption": "{date} · net {net} · {relevant} of 9 stories with an institutional stake",

  "filter.all": "all nine",
  "filter.erosion": "erosion only",
  "filter.strengthening": "strengthening",
  "filter.contested": "contested facts",
  "filter.count": "{shown} of {total}",

  "section.readings_one": "1 reading",
  "section.readings_other": "{n} readings",
  "section.empty": "Nothing here under this filter.",

  "story.rankLabel": "rank {n} of three",
  "story.noStake": "no institutional stake",
  "story.read": "read the analysis",
  "story.close": "close",
  "story.why": "Why it matters",
  "story.inWords": "Reading, in words",
  "story.claims": "Claims, sorted by how well they stand up",
  "story.framing": "Framing check",
  "story.devices": "Devices.",
  "story.omitted": "Left out.",
  "story.propaganda": "Propaganda markers.",
  "story.unknown": "Not known",
  "story.counter": "Strongest counter-reading",
  "story.watch": "What would settle it",
  "story.score": "score",
  "story.copy": "copy summary",
  "story.copied": "copied",
  "story.diversity": "Source diversity {d} · credibility {c} · novelty {n}",
  "story.confidence": "{n}% confident",

  "deep.eyebrow": "Deep dive · one story, all the way down",
  "deep.background": "How we got here",
  "deep.mechanisms": "The machinery",
  "deep.stakes": "Democratic stakes",
  "deep.precedent": "Precedent, and where it breaks",
  "deep.stakeholders": "Who wants what",
  "deep.scenarios": "Next three to twelve months",
  "deep.watch": "What to watch",
  "deep.open": "Still open",
  "deep.counter": "The case that this matters less than the above",
  "deep.confidence": "analysis confidence {n}%",
  "deep.indicators": "watch: {list}",

  "colophon.pipeline": "{fetched} articles from {sources} sources → {clusters} stories → 9 selected",
  "colophon.generated": "generated {when} UTC",

  "empty.title": "No digest yet",
  "empty.body": "Start the API and run {cmd}.",
};

const bg: Dict = {
  "masthead.place": "София",
  "masthead.keys": "j / k придвижване · o отваряне",
  "masthead.moved": "Днес институциите се отместиха с",
  "masthead.suffix": ".",
  "masthead.fallbackNote": "Девет истории, {n} от тях с институционален залог.",
  "banner.sample": "Примерни данни. API-то не върна бюлетин — изпълни {cmd}.",
  "banner.untranslated": "Този бюлетин още не е преведен. Изпълни {cmd} за български.",

  "trace.label": "{n}-дневна крива · мащаб ±{peak}",
  "trace.caption": "{date} · нето {net} · {relevant} от 9 истории с институционален залог",

  "filter.all": "всичките девет",
  "filter.erosion": "само ерозия",
  "filter.strengthening": "укрепване",
  "filter.contested": "оспорвани факти",
  "filter.count": "{shown} от {total}",

  "section.readings_one": "1 отчитане",
  "section.readings_other": "{n} отчитания",
  "section.empty": "Няма нищо при този филтър.",

  "story.rankLabel": "позиция {n} от три",
  "story.noStake": "без институционален залог",
  "story.read": "виж анализа",
  "story.close": "затвори",
  "story.why": "Защо е важно",
  "story.inWords": "Отчитането, с думи",
  "story.claims": "Твърдения, подредени по достоверност",
  "story.framing": "Как е поднесена новината",
  "story.devices": "Похвати.",
  "story.omitted": "Пропуснато.",
  "story.propaganda": "Пропагандни белези.",
  "story.unknown": "Неизвестно",
  "story.counter": "Най-силният контрапрочит",
  "story.watch": "Какво би дало отговор",
  "story.score": "оценка",
  "story.copy": "копирай резюмето",
  "story.copied": "копирано",
  "story.diversity": "Разнообразие на източниците {d} · достоверност {c} · новост {n}",
  "story.confidence": "{n}% увереност",

  "deep.eyebrow": "Задълбочено · една история, докрай",
  "deep.background": "Как стигнахме дотук",
  "deep.mechanisms": "Механиката",
  "deep.stakes": "Демократичният залог",
  "deep.precedent": "Прецедент и къде не важи",
  "deep.stakeholders": "Кой какво иска",
  "deep.scenarios": "Следващите три до дванайсет месеца",
  "deep.watch": "Какво да следим",
  "deep.open": "Все още открито",
  "deep.counter": "Аргументът, че това значи по-малко от горното",
  "deep.confidence": "увереност в анализа {n}%",
  "deep.indicators": "следи: {list}",

  "colophon.pipeline": "{fetched} статии от {sources} източника → {clusters} истории → 9 избрани",
  "colophon.generated": "генерирано {when} UTC",

  "empty.title": "Още няма бюлетин",
  "empty.body": "Стартирай API-то и изпълни {cmd}.",
};

const DICTS: Record<Locale, Dict> = { en, bg };

export function translate(locale: Locale, key: string, vars?: Record<string, string | number>): string {
  const raw = DICTS[locale][key] ?? DICTS.en[key] ?? key;
  if (!vars) return raw;
  return raw.replace(/\{(\w+)\}/g, (_, name) => String(vars[name] ?? `{${name}}`));
}

// --------------------------------------------------------------------------- //
// The rubric's own vocabulary. These are terms of art, not UI copy.
// --------------------------------------------------------------------------- //
export const DIMENSIONS: Record<Locale, Record<string, string>> = {
  en: {
    rule_of_law: "rule of law",
    checks_and_balances: "checks and balances",
    electoral_integrity: "electoral integrity",
    media_freedom: "media freedom",
    civil_liberties: "civil liberties",
    anticorruption: "anticorruption",
    minority_rights: "minority rights",
    civic_space: "civic space",
    information_integrity: "information integrity",
    state_capacity: "state capacity",
  },
  bg: {
    rule_of_law: "върховенство на правото",
    checks_and_balances: "спирачки и противотежести",
    electoral_integrity: "честност на изборите",
    media_freedom: "свобода на медиите",
    civil_liberties: "граждански свободи",
    anticorruption: "борба с корупцията",
    minority_rights: "права на малцинствата",
    civic_space: "гражданско пространство",
    information_integrity: "достоверност на информацията",
    state_capacity: "капацитет на държавата",
  },
};

export const DIRECTIONS: Record<Locale, Record<number, string>> = {
  en: {
    [-2]: "severe erosion",
    [-1]: "erosion",
    0: "neutral",
    1: "strengthening",
    2: "significant strengthening",
  },
  bg: {
    [-2]: "тежка ерозия",
    [-1]: "ерозия",
    0: "неутрално",
    1: "укрепване",
    2: "значително укрепване",
  },
};

export const CLAIMS: Record<Locale, Record<string, string>> = {
  en: {
    established: "established",
    reported: "reported",
    contested: "contested",
    speculative: "speculative",
  },
  bg: {
    established: "потвърдено",
    reported: "съобщено",
    contested: "оспорвано",
    speculative: "предположение",
  },
};

export const CATEGORIES: Record<Locale, Record<string, string>> = {
  en: {
    bg_politics: "Bulgarian politics",
    global_politics: "Global politics",
    ai_tech_business: "AI · tech · business",
  },
  bg: {
    bg_politics: "Българска политика",
    global_politics: "Световна политика",
    ai_tech_business: "ИИ · технологии · бизнес",
  },
};

/** Editorial lean, abbreviated for the source strip. */
export const LEANS: Record<Locale, Record<string, string>> = {
  en: {
    left: "L", center_left: "CL", center: "C", center_right: "CR", right: "R",
    state_aligned: "state", oligarch_linked: "owner", unknown: "?",
  },
  bg: {
    left: "Л", center_left: "ЦЛ", center: "Ц", center_right: "ЦД", right: "Д",
    state_aligned: "държ.", oligarch_linked: "собств.", unknown: "?",
  },
};

export const DATE_LOCALE: Record<Locale, string> = { en: "en-GB", bg: "bg-BG" };

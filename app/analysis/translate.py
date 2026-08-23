"""Translate a finished digest into another language.

The analyst writes in English by design — one language keeps the rubric consistent and
the clustering comparable across a mixed-language source pool. Translation is therefore a
separate pass over the finished product, not a second analysis.

The unit of translation is a whole `StoryAnalysis`, returned in the same schema. Asking
for parallel lists of loose strings invites drift between a rationale and the dimension
it belongs to; asking for the same object back cannot. Numbers and enums are restored
from the original afterwards regardless of what comes back, so a translation can never
change a score.
"""
from __future__ import annotations

import asyncio

import structlog

from app.analysis.llm import LLMClient
from app.config import settings
from app.models.schemas import DailyDigest, DeepDive, DigestTranslation, StoryAnalysis

log = structlog.get_logger(__name__)

LANGUAGE_NAMES = {"bg": "Bulgarian"}

SYSTEM_TRANSLATE = """\
You translate a news analysis into {language}, returning the same JSON structure with the
same fields.

Rules:
  - Translate only human-readable prose. Leave every number, score, enum value, date, URL
    and field name exactly as it is.
  - Keep `cluster_key`, `category`, `dimension`, `status` and all numeric fields byte-identical.
  - Institution and party names: use the established {language} form where one exists
    ("Supreme Judicial Council" -> "Висш съдебен съвет", "European Commission" ->
    "Европейска комисия"). Personal names transliterate. Give an unfamiliar foreign
    institution its {language} rendering with the original in brackets on first use.
  - NEVER substitute a different organisation. A party you do not recognise is not a
    typo for a party you do: translate its name literally or transliterate it, and keep
    its abbreviation derived from the name in front of you. Silently promoting an
    unfamiliar party to a well-known one changes who did the thing, which is the one
    error this system cannot absorb.
  - This is analysis, not press-release copy. Match the register: plain, specific,
    declarative. Do not soften a judgement, add hedging the original does not have, or
    make an erosion finding sound more polite than it is.
  - Do not add, drop or reorder any list item.

Return only the JSON object.
"""

SOURCE_NAMES_BLOCK = """

ORIGINAL HEADLINES from the reports this analysis was written on. Where a person, party
or institution appears here already in {language}, use exactly that form — it is the
authoritative spelling and it outranks anything you recall:
{headlines}
"""


def _restore_invariants(original: StoryAnalysis, translated: StoryAnalysis) -> StoryAnalysis:
    """Numbers and enums come from the original, whatever the model returned. A
    translation must never move a score."""
    impacts = []
    for src, dst in zip(original.democracy.impacts, translated.democracy.impacts, strict=False):
        impacts.append(dst.model_copy(update={
            "dimension": src.dimension, "direction": src.direction, "confidence": src.confidence,
        }))
    # If the model dropped or invented impacts, keep the original set outright.
    if len(impacts) != len(original.democracy.impacts):
        impacts = original.democracy.impacts

    claims = []
    for src, dst in zip(original.claims, translated.claims, strict=False):
        claims.append(dst.model_copy(update={"status": src.status}))
    if len(claims) != len(original.claims):
        claims = original.claims

    democracy = translated.democracy.model_copy(update={
        "relevant": original.democracy.relevant,
        "net_direction": original.democracy.net_direction,
        "significance": original.democracy.significance,
        "impacts": impacts,
    })
    bias = translated.bias.model_copy(update={
        "source_diversity": original.bias.source_diversity,
    })
    return translated.model_copy(update={
        "cluster_key": original.cluster_key,
        "category": original.category,
        "claims": claims,
        "democracy": democracy,
        "bias": bias,
        "impact_scope": original.impact_scope,
        "novelty": original.novelty,
        "credibility": original.credibility,
        "entities": original.entities,
        "tags": original.tags,
    })


async def _translate_one(client: LLMClient, obj, schema, language: str, purpose: str,
                         max_tokens: int = 6000, headlines: list[str] | None = None):
    """`max_tokens` has to reflect the real size of the thing being translated.

    The Claude Code backend derives its timeout from it, and understating a deep dive —
    14.6k tokens of output, sent as 8000 — is what killed the first run at 420s.
    """
    system = SYSTEM_TRANSLATE.format(language=language)
    if headlines:
        system += SOURCE_NAMES_BLOCK.format(
            language=language, headlines="\n".join(f"  - {h}" for h in headlines))
    return (await client.complete_json(
        system=system,
        user=obj.model_dump_json(),
        schema=schema,
        model=settings.llm_model_analysis,
        max_tokens=max_tokens,
        effort="low",
        purpose=purpose,
    )).data


async def translate_digest(client: LLMClient, digest: DailyDigest, lang: str = "bg",
                           existing: DigestTranslation | None = None) -> DigestTranslation:
    """One call per story plus one for the deep dive, run concurrently.

    Resumable: anything already present in `existing` is skipped. A run cut short by a
    rate limit therefore costs nothing to pick up again — which matters when the backend
    is a subscription with a daily ceiling rather than metered credits.
    """
    language = LANGUAGE_NAMES.get(lang, lang)
    done = existing or DigestTranslation()

    async def story(item) -> tuple[str, StoryAnalysis | None]:
        analysis = item.analysis
        if analysis.cluster_key in done.items:
            return analysis.cluster_key, done.items[analysis.cluster_key]
        try:
            out = await _translate_one(
                client, analysis, StoryAnalysis, language, "translate",
                headlines=[r.title for r in item.refs if r.title],
            )
            return analysis.cluster_key, _restore_invariants(analysis, out)
        except Exception as exc:
            log.warning("translate.story_failed", key=analysis.cluster_key, error=str(exc)[:200])
            return analysis.cluster_key, None

    async def deep() -> DeepDive | None:
        if digest.deep_dive is None:
            return None
        if done.deep_dive is not None:
            return done.deep_dive
        try:
            refs = [r.title for r in (digest.deep_dive_refs or []) if r.title]
            out = await _translate_one(client, digest.deep_dive, DeepDive, language,
                                       "translate_deepdive", max_tokens=18000,
                                       headlines=refs)
            # Probabilities and confidence are findings, not prose.
            scenarios = [d.model_copy(update={"probability": s.probability})
                         for s, d in zip(digest.deep_dive.scenarios, out.scenarios, strict=False)]
            return out.model_copy(update={
                "cluster_key": digest.deep_dive.cluster_key,
                "confidence": digest.deep_dive.confidence,
                "scenarios": scenarios or digest.deep_dive.scenarios,
            })
        except Exception as exc:
            log.warning("translate.deepdive_failed", error=str(exc)[:200])
            return None

    class _Note(__import__("pydantic").BaseModel):
        note: str

    async def note() -> str | None:
        if not digest.editorial_note:
            return None
        if done.editorial_note:
            return done.editorial_note
        try:
            res = await client.complete_json(
                system=(f"Translate this editor's note into {language}. Same register: plain and "
                        "specific, no hype. Put the translation in the `note` field."),
                user=digest.editorial_note, schema=_Note,
                model=settings.llm_model_analysis, max_tokens=1200, effort="low",
                purpose="translate",
            )
            return res.data.note
        except Exception as exc:
            log.warning("translate.note_failed", error=str(exc)[:200])
            return None

    results = await asyncio.gather(
        *(story(i) for i in digest.items), deep(), note()
    )
    *stories, deep_dive, editorial = results

    items = {key: value for key, value in stories if value is not None}
    log.info("translate.done", lang=lang, stories=len(items), of=len(digest.items),
             deep_dive=bool(deep_dive), resumed=len(done.items))
    return DigestTranslation(editorial_note=editorial, items=items, deep_dive=deep_dive)


def is_complete(digest: DailyDigest, translation: DigestTranslation | None) -> bool:
    if translation is None:
        return False
    if len(translation.items) < len(digest.items):
        return False
    if digest.deep_dive is not None and translation.deep_dive is None:
        return False
    return not (digest.editorial_note and not translation.editorial_note)

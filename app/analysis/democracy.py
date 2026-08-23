"""Democracy scoring helpers.

The LLM produces per-dimension judgements; this module turns them into numbers the
selector and the dashboard can use, and enforces sanity (e.g. an "erosion" verdict
with no named mechanism is downgraded).
"""
from __future__ import annotations

from app.models.schemas import DemocracyAssessment, DemocracyDimension, StoryAnalysis

# Not all dimensions are equally load-bearing for regime health. These weights are a
# judgement call and deliberately visible/tunable rather than buried in a prompt.
DIMENSION_WEIGHT: dict[DemocracyDimension, float] = {
    DemocracyDimension.RULE_OF_LAW: 1.00,
    DemocracyDimension.CHECKS_AND_BALANCES: 1.00,
    DemocracyDimension.ELECTORAL_INTEGRITY: 1.00,
    DemocracyDimension.MEDIA_FREEDOM: 0.90,
    DemocracyDimension.ANTICORRUPTION: 0.85,
    DemocracyDimension.CIVIL_LIBERTIES: 0.85,
    DemocracyDimension.CIVIC_SPACE: 0.75,
    DemocracyDimension.INFORMATION_INTEGRITY: 0.75,
    DemocracyDimension.MINORITY_RIGHTS: 0.70,
    DemocracyDimension.STATE_CAPACITY: 0.55,
}

SEVERITY_LABEL = {
    -2: "severe erosion", -1: "erosion", 0: "neutral / mixed",
    1: "strengthening", 2: "significant strengthening",
}


def weighted_direction(assessment: DemocracyAssessment) -> float:
    """Confidence- and weight-adjusted net direction in [-2, 2]."""
    if not assessment.relevant or not assessment.impacts:
        return 0.0
    num = sum(i.direction * DIMENSION_WEIGHT.get(i.dimension, 0.6) * i.confidence
              for i in assessment.impacts)
    den = sum(DIMENSION_WEIGHT.get(i.dimension, 0.6) * i.confidence for i in assessment.impacts)
    return num / den if den else 0.0


def democracy_score(analysis: StoryAnalysis) -> float:
    """0-1 selection term. Magnitude matters, direction does not: a story where
    democracy is meaningfully *strengthened* is as newsworthy as one where it erodes."""
    a = analysis.democracy
    if not a.relevant:
        return 0.0
    magnitude = min(abs(weighted_direction(a)) / 2.0, 1.0)
    return round(0.65 * a.significance + 0.35 * magnitude, 4)


def sanity_flags(analysis: StoryAnalysis) -> list[str]:
    """Cheap guards against the model over-claiming. Surfaced in the dashboard, and
    used to damp scores in the selector."""
    flags: list[str] = []
    a = analysis.democracy
    if a.relevant and a.significance > 0.7 and analysis.credibility < 0.5:
        flags.append("high_significance_low_credibility")
    if a.relevant and not a.impacts:
        flags.append("relevant_but_no_dimensions")
    if a.relevant and abs(a.net_direction) >= 2 and analysis.bias.source_diversity < 0.4:
        flags.append("strong_verdict_thin_sourcing")
    if any(len(i.rationale.split()) < 6 for i in a.impacts):
        flags.append("thin_rationale")
    if analysis.contrarian_read is None and a.relevant:
        flags.append("no_counterview")
    return flags


def summarize_day(analyses: list[StoryAnalysis]) -> dict[str, float | int]:
    """Aggregate indicators for the dashboard's trend line."""
    relevant = [a for a in analyses if a.democracy.relevant]
    if not relevant:
        return {"stories": len(analyses), "democracy_relevant": 0, "net_direction": 0.0}
    net = sum(weighted_direction(a.democracy) for a in relevant) / len(relevant)
    return {
        "stories": len(analyses),
        "democracy_relevant": len(relevant),
        "net_direction": round(net, 3),
        "erosion_stories": sum(1 for a in relevant if weighted_direction(a.democracy) < -0.3),
        "strengthening_stories": sum(1 for a in relevant if weighted_direction(a.democracy) > 0.3),
        "mean_significance": round(sum(a.democracy.significance for a in relevant) / len(relevant), 3),
    }

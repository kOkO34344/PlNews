from app.analysis.analyzer import AnalysisOutcome
from app.analysis.democracy import democracy_score, sanity_flags, weighted_direction
from app.models.schemas import Category, Lean
from app.selection.selector import PER_CATEGORY, score_candidate, select_333
from tests.factories import make_analysis, make_cluster, make_ref


def _outcome(key: str, *, significance=0.8, novelty=0.7, category=Category.BG_POLITICS,
             refs=None, entities=None) -> AnalysisOutcome:
    cluster = make_cluster(key, category, refs=refs)
    analysis = make_analysis(key, category, significance=significance, novelty=novelty,
                             entities=entities)
    return AnalysisOutcome(cluster=cluster, analysis=analysis)


def test_democracy_score_zero_when_not_relevant():
    a = make_analysis()
    a = a.model_copy(update={"democracy": a.democracy.model_copy(update={"relevant": False})})
    assert democracy_score(a) == 0.0


def test_weighted_direction_respects_confidence():
    a = make_analysis(direction=-2)
    assert weighted_direction(a.democracy) < 0


def test_single_source_is_penalised():
    solo = _outcome("solo", refs=[make_ref()])
    duo = _outcome("duo")
    s_solo = score_candidate(solo, {}, set())
    s_duo = score_candidate(duo, {}, set())
    assert s_solo.penalties > s_duo.penalties
    assert s_solo.total < s_duo.total


def test_repeat_story_with_low_novelty_is_penalised():
    o = _outcome("running", novelty=0.2)
    fresh = score_candidate(o, {}, set())
    repeat = score_candidate(o, {}, {"running"})
    assert repeat.total < fresh.total


def test_select_333_returns_three_per_category():
    outcomes = []
    for i in range(5):
        outcomes.append(_outcome(f"bg{i}", significance=0.9 - i * 0.1, category=Category.BG_POLITICS))
        outcomes.append(_outcome(f"gl{i}", significance=0.9 - i * 0.1, category=Category.GLOBAL_POLITICS))
        outcomes.append(_outcome(f"ai{i}", significance=0.9 - i * 0.1, category=Category.AI_TECH_BUSINESS))

    items = select_333(outcomes)
    for cat in Category:
        picked = [i for i in items if i.category == cat]
        assert len(picked) == PER_CATEGORY
        assert [i.rank for i in picked] == [1, 2, 3]


def test_selection_score_is_explainable():
    score = score_candidate(_outcome("k"), {}, set())
    assert "democracy" in score.explanation and "credibility" in score.explanation


def test_sanity_flags_catch_overclaiming():
    a = make_analysis(significance=0.9, credibility=0.3)
    assert "high_significance_low_credibility" in sanity_flags(a)

import pytest
from pydantic import ValidationError

from app.analysis import prompts
from app.analysis.llm import LLMError, extract_json
from app.models.schemas import DeepDive, StoryAnalysis
from tests.factories import make_analysis, make_cluster


def test_extract_json_tolerates_fences_and_prose():
    assert extract_json('```json\n{"a": 1}\n```') == {"a": 1}
    assert extract_json('Sure! {"a": 2} hope that helps') == {"a": 2}
    with pytest.raises(LLMError):
        extract_json("no json here")


def test_analysis_schema_rejects_extra_fields():
    payload = make_analysis().model_dump(mode="json")
    payload["editorialised_opinion"] = "we think this is terrible"
    with pytest.raises(ValidationError):
        StoryAnalysis.model_validate(payload)


def test_democracy_direction_is_bounded():
    payload = make_analysis().model_dump(mode="json")
    payload["democracy"]["impacts"][0]["direction"] = 7
    with pytest.raises(ValidationError):
        StoryAnalysis.model_validate(payload)


def test_prompts_embed_the_output_schema():
    assert "cluster_key" in prompts.SYSTEM_ANALYSIS
    assert "DEMOCRACY RUBRIC" in prompts.SYSTEM_ANALYSIS
    assert "scenarios" in prompts.SYSTEM_DEEPDIVE


def test_user_prompt_includes_lean_metadata():
    cluster = make_cluster()
    user = prompts.build_analysis_user_prompt(cluster, {})
    assert "lean=" in user and "reliability=" in user
    assert cluster.key in user


def test_deep_dive_requires_at_least_two_scenarios():
    from tests.factories import make_deep_dive

    payload = make_deep_dive().model_dump(mode="json")
    payload["scenarios"] = payload["scenarios"][:1]
    with pytest.raises(ValidationError):
        DeepDive.model_validate(payload)

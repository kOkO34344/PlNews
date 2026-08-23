"""Regression tests for the request shape we send to the Messages API.

Assistant prefill and sampling parameters were both fine on older models and are both
a 400 on Sonnet 5 / Opus 5. Nothing in the pipeline would have caught that before the
first real (billed) run, so it is pinned here.
"""
from __future__ import annotations

import json
from types import SimpleNamespace

import pytest
from pydantic import BaseModel

from app.analysis.llm import AnthropicClient, Refusal


class Tiny(BaseModel):
    note: str


class FakeMessages:
    def __init__(self, payload=None, raise_on_first=None):
        self.calls: list[dict] = []
        self.payload = payload if payload is not None else {"note": "ok"}
        self.raise_on_first = raise_on_first

    async def create(self, **kwargs):
        self.calls.append(kwargs)
        if self.raise_on_first and len(self.calls) == 1:
            raise self.raise_on_first
        return SimpleNamespace(
            content=[SimpleNamespace(type="text", text=json.dumps(self.payload))],
            usage=SimpleNamespace(input_tokens=100, output_tokens=20),
            stop_reason="end_turn",
        )


def make_client(fake: FakeMessages, **kw) -> AnthropicClient:
    client = AnthropicClient(api_key="test-key", **kw)
    client._client = SimpleNamespace(messages=fake)
    return client


async def test_request_carries_no_prefill_and_no_temperature():
    fake = FakeMessages()
    result = await make_client(fake).complete_json(
        system="sys", user="usr", schema=Tiny, model="claude-sonnet-5", effort="low",
    )
    (call,) = fake.calls
    assert [m["role"] for m in call["messages"]] == ["user"], "assistant prefill is a 400 now"
    assert "temperature" not in call and "top_p" not in call and "top_k" not in call
    assert call["output_config"]["effort"] == "low"
    assert result.data.note == "ok"
    assert (result.tokens_in, result.tokens_out) == (100, 20)


async def test_structured_output_is_requested_by_default():
    fake = FakeMessages()
    await make_client(fake).complete_json(
        system="s", user="u", schema=Tiny, model="claude-sonnet-5",
    )
    fmt = fake.calls[0]["output_config"]["format"]
    assert fmt["type"] == "json_schema"
    assert fmt["schema"]["properties"]["note"]["type"] == "string"


async def test_schema_rejection_falls_back_once_and_keeps_going():
    rejection = Exception("output_config.format: unsupported json_schema keyword")
    rejection.status_code = 400  # type: ignore[attr-defined]
    fake = FakeMessages(raise_on_first=rejection)
    client = make_client(fake)

    result = await client.complete_json(system="s", user="u", schema=Tiny, model="claude-sonnet-5")
    assert result.data.note == "ok"
    assert "format" not in fake.calls[1]["output_config"], "retry must drop the schema"

    # And the whole run stops asking for it, rather than eating a 400 per story.
    await client.complete_json(system="s", user="u", schema=Tiny, model="claude-sonnet-5")
    assert "format" not in fake.calls[2]["output_config"]


async def test_other_400s_are_not_swallowed():
    other = Exception("max_tokens is too large")
    other.status_code = 400  # type: ignore[attr-defined]
    with pytest.raises(Exception, match="max_tokens"):
        await make_client(FakeMessages(raise_on_first=other)).complete_json(
            system="s", user="u", schema=Tiny, model="claude-sonnet-5",
        )


async def test_refusal_is_surfaced_not_parsed():
    class Refusing(FakeMessages):
        async def create(self, **kwargs):
            self.calls.append(kwargs)
            return SimpleNamespace(content=[], stop_reason="refusal",
                                   stop_details=SimpleNamespace(category="cyber"),
                                   usage=SimpleNamespace(input_tokens=10, output_tokens=0))

    fake = Refusing()
    with pytest.raises(Refusal, match="declined"):
        await make_client(fake).complete_json(
            system="s", user="u", schema=Tiny, model="claude-sonnet-5",
        )
    assert len(fake.calls) == 1, "a refusal must not be retried — it costs tokens to be told no again"

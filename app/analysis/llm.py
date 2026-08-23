"""Thin, typed wrapper around the Anthropic Messages API.

Everything the rest of the app needs: JSON-only calls that come back as validated
Pydantic objects, bounded concurrency, retries, and a per-run token budget.
Swap `AnthropicClient` for another provider by implementing `LLMClient`.
"""
from __future__ import annotations

import asyncio
import json
import re
import time
from dataclasses import dataclass, field
from typing import Any, Generic, Protocol, TypeVar

import structlog
from pydantic import BaseModel, ValidationError
from tenacity import retry, retry_if_exception_type, stop_after_attempt, wait_exponential

from app.config import settings

log = structlog.get_logger(__name__)
T = TypeVar("T", bound=BaseModel)

_FENCE = re.compile(r"^\s*```(?:json)?\s*|\s*```\s*$", re.MULTILINE)


class LLMError(RuntimeError):
    pass


class BudgetExceeded(LLMError):
    pass


@dataclass
class Usage:
    tokens_in: int = 0
    tokens_out: int = 0
    calls: int = 0
    errors: int = 0
    latency_ms: int = 0

    def add(self, tin: int, tout: int, ms: int) -> None:
        self.tokens_in += tin
        self.tokens_out += tout
        self.latency_ms += ms
        self.calls += 1


@dataclass
class LLMResult(Generic[T]):
    data: T
    model: str
    tokens_in: int
    tokens_out: int
    latency_ms: int
    raw: str = field(repr=False, default="")


class LLMClient(Protocol):
    async def complete_json(
        self, *, system: str, user: str, schema: type[T], model: str, max_tokens: int = 4096,
        temperature: float = 0.2, purpose: str = "analysis",
    ) -> LLMResult[T]: ...


def extract_json(text: str) -> dict[str, Any]:
    """Models occasionally wrap JSON in prose or fences. Be forgiving, once."""
    cleaned = _FENCE.sub("", text).strip()
    try:
        return json.loads(cleaned)
    except json.JSONDecodeError:
        start, end = cleaned.find("{"), cleaned.rfind("}")
        if start == -1 or end <= start:
            raise LLMError(f"no JSON object in response: {text[:300]!r}") from None
        return json.loads(cleaned[start : end + 1])


class AnthropicClient:
    """Bounded-concurrency Anthropic client that returns validated Pydantic models."""

    def __init__(self, api_key: str | None = None, max_concurrency: int | None = None,
                 token_budget: int | None = None) -> None:
        from anthropic import AsyncAnthropic  # local import keeps import-time cheap

        self._client = AsyncAnthropic(api_key=api_key or settings.anthropic_api_key)
        self._sem = asyncio.Semaphore(max_concurrency or settings.llm_max_concurrency)
        self._budget = token_budget or settings.llm_daily_token_budget
        self.usage = Usage()

    def _check_budget(self) -> None:
        spent = self.usage.tokens_in + self.usage.tokens_out
        if spent >= self._budget:
            raise BudgetExceeded(f"token budget exhausted: {spent}/{self._budget}")

    @retry(
        reraise=True,
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=2, min=2, max=30),
        retry=retry_if_exception_type((LLMError, ValidationError)),
    )
    async def complete_json(
        self, *, system: str, user: str, schema: type[T], model: str, max_tokens: int = 4096,
        temperature: float = 0.2, purpose: str = "analysis",
    ) -> LLMResult[T]:
        self._check_budget()
        async with self._sem:
            t0 = time.perf_counter()
            resp = await self._client.messages.create(
                model=model,
                max_tokens=max_tokens,
                temperature=temperature,
                system=system,
                messages=[
                    {"role": "user", "content": user},
                    # Prefill forces the model straight into JSON — no preamble to strip.
                    {"role": "assistant", "content": "{"},
                ],
            )
            ms = int((time.perf_counter() - t0) * 1000)

        raw = "{" + "".join(b.text for b in resp.content if getattr(b, "type", "") == "text")
        tin = getattr(resp.usage, "input_tokens", 0)
        tout = getattr(resp.usage, "output_tokens", 0)
        self.usage.add(tin, tout, ms)

        try:
            data = schema.model_validate(extract_json(raw))
        except (ValidationError, LLMError) as exc:
            self.usage.errors += 1
            log.warning("llm.invalid_json", purpose=purpose, model=model, error=str(exc)[:400])
            raise

        log.info("llm.ok", purpose=purpose, model=model, tokens_in=tin, tokens_out=tout, ms=ms)
        return LLMResult(data=data, model=model, tokens_in=tin, tokens_out=tout, latency_ms=ms, raw=raw)


class StubClient:
    """Offline client for tests and dry runs: returns schema-valid filler."""

    def __init__(self, factory=None) -> None:
        self.factory = factory
        self.usage = Usage()
        self.calls: list[tuple[str, str]] = []

    async def complete_json(self, *, system: str, user: str, schema: type[T], model: str,
                            max_tokens: int = 4096, temperature: float = 0.2,
                            purpose: str = "analysis") -> LLMResult[T]:
        self.calls.append((purpose, user[:200]))
        if self.factory is None:
            raise NotImplementedError("StubClient needs a factory(schema, user) callable")
        data = self.factory(schema, user)
        self.usage.add(0, 0, 0)
        return LLMResult(data=data, model="stub", tokens_in=0, tokens_out=0, latency_ms=0)


def get_llm_client() -> LLMClient:
    if not settings.anthropic_api_key:
        log.warning("llm.no_api_key", msg="ANTHROPIC_API_KEY unset — LLM calls will fail")
    return AnthropicClient()

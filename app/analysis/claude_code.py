"""LLM backend that runs through the local Claude Code CLI.

Why this exists: `claude -p` authenticates with the user's Claude Code subscription,
so a daily digest costs nothing extra in API credits. It is the same models behind
the same account — what changes is which meter the run comes off.

The trade-off is harness overhead. Claude Code sends its own system prompt and tool
definitions with every invocation, which is ~21.7k tokens by default. Replacing the
system prompt and disallowing the tool set cuts that to ~4.8k, but it never reaches
zero the way a direct API call does, so a run here consumes roughly 1.5-2x the tokens
of the same run on the API. Free in dollars, not free in rate limit.

Measured on Claude Code 2.1.241 (2026-08-23), one trivial call:

    default                             21,753 cache-creation tokens
    --system-prompt                     16,971
    --system-prompt --disallowedTools    4,812
"""
from __future__ import annotations

import asyncio
import json
import shutil
import tempfile
import time
from pathlib import Path
from typing import Any, TypeVar

import structlog
from pydantic import BaseModel, ValidationError

from app.analysis.llm import LLMError, LLMResult, Refusal, Usage
from app.config import settings

log = structlog.get_logger(__name__)
T = TypeVar("T", bound=BaseModel)

# Every tool the harness would otherwise define and ship on each call. Nothing here is
# useful for "read these articles and return JSON", and each definition costs tokens.
UNUSED_TOOLS = (
    "Bash Read Write Edit Glob Grep WebFetch WebSearch Task TodoWrite NotebookEdit "
    "SlashCommand Skill Agent Artifact"
)

DEFAULT_TIMEOUT_S = 420


class ClaudeCodeUnavailable(LLMError):
    """The CLI is missing or not logged in."""


def cli_path() -> str | None:
    return shutil.which("claude")


class ClaudeCodeClient:
    """Implements the same `LLMClient` protocol as `AnthropicClient`."""

    #: --json-schema constrains decoding, so the prompt need not carry the schema too.
    enforces_schema = True

    def __init__(self, *, max_concurrency: int | None = None, timeout_s: int = DEFAULT_TIMEOUT_S,
                 workdir: Path | None = None) -> None:
        self._cli = cli_path()
        if not self._cli:
            raise ClaudeCodeUnavailable(
                "`claude` is not on PATH. Install Claude Code, or set LLM_BACKEND=api."
            )
        # Subscription rate limits are tighter than API concurrency, and each call carries
        # the harness overhead, so default lower than the API client does.
        self._sem = asyncio.Semaphore(max_concurrency or min(settings.llm_max_concurrency, 2))
        self._timeout = timeout_s
        # A neutral directory: run from the repo and the CLI would pull the project into
        # scope. Nothing about news analysis should see this codebase.
        self._workdir = workdir or Path(tempfile.mkdtemp(prefix="plnews-llm-"))
        self.usage = Usage()
        self.cost_usd = 0.0

    def _argv(self, *, system: str, schema: type[T], model: str, effort: str) -> list[str]:
        return [
            self._cli, "-p",
            "--output-format", "json",
            "--json-schema", json.dumps(schema.model_json_schema(), separators=(",", ":")),
            "--system-prompt", system,
            "--model", model,
            "--effort", effort,
            "--safe-mode",              # no CLAUDE.md, skills, plugins, hooks or MCP; auth still works
            "--no-session-persistence",  # 36 sessions a day is not an archive anyone wants
            "--disallowedTools", UNUSED_TOOLS,
        ]

    async def complete_json(
        self, *, system: str, user: str, schema: type[T], model: str, max_tokens: int = 4096,
        effort: str = "medium", purpose: str = "analysis",
    ) -> LLMResult[T]:
        argv = self._argv(system=system, schema=schema, model=model, effort=effort)

        async with self._sem:
            t0 = time.perf_counter()
            proc = await asyncio.create_subprocess_exec(
                *argv,
                stdin=asyncio.subprocess.PIPE,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                cwd=str(self._workdir),
            )
            try:
                out, err = await asyncio.wait_for(
                    proc.communicate(user.encode("utf-8")), timeout=self._timeout
                )
            except TimeoutError:
                proc.kill()
                await proc.wait()
                self.usage.errors += 1
                raise LLMError(f"claude timed out after {self._timeout}s") from None
            ms = int((time.perf_counter() - t0) * 1000)

        if proc.returncode != 0:
            self.usage.errors += 1
            raise LLMError(f"claude exited {proc.returncode}: {err.decode('utf-8', 'replace')[:400]}")

        try:
            envelope: dict[str, Any] = json.loads(out.decode("utf-8"))
        except json.JSONDecodeError as exc:
            self.usage.errors += 1
            raise LLMError(f"claude returned non-JSON: {out[:300]!r}") from exc

        usage = envelope.get("usage") or {}
        # Cache-creation tokens are real input tokens; counting only `input_tokens` would
        # under-report a call by an order of magnitude and make the budget meaningless.
        tin = (int(usage.get("input_tokens", 0))
               + int(usage.get("cache_creation_input_tokens", 0))
               + int(usage.get("cache_read_input_tokens", 0)))
        tout = int(usage.get("output_tokens", 0))
        self.usage.add(tin, tout, ms)
        self.cost_usd += float(envelope.get("total_cost_usd") or 0.0)

        if envelope.get("is_error") or envelope.get("subtype") not in (None, "success"):
            self.usage.errors += 1
            detail = envelope.get("result") or envelope.get("api_error_status") or envelope.get("subtype")
            raise LLMError(f"claude reported failure: {str(detail)[:400]}")
        if envelope.get("stop_reason") == "refusal":
            self.usage.errors += 1
            raise Refusal(f"model declined: {envelope.get('result')}")

        payload = envelope.get("structured_output")
        if payload is None:
            # --json-schema normally guarantees structured_output; fall back to the text.
            from app.analysis.llm import extract_json

            payload = extract_json(str(envelope.get("result", "")))

        try:
            data = schema.model_validate(payload)
        except ValidationError:
            self.usage.errors += 1
            log.warning("claude_code.invalid_payload", purpose=purpose,
                        keys=sorted(payload)[:12] if isinstance(payload, dict) else type(payload))
            raise

        log.info("claude_code.ok", purpose=purpose, model=model, effort=effort,
                 tokens_in=tin, tokens_out=tout, ms=ms,
                 notional_usd=round(float(envelope.get("total_cost_usd") or 0.0), 4))
        return LLMResult(data=data, model=model, tokens_in=tin, tokens_out=tout, latency_ms=ms,
                         raw=str(envelope.get("result", "")))

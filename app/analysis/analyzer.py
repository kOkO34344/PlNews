"""Phase 2: run the analyst prompt over every candidate cluster, concurrently."""
from __future__ import annotations

import asyncio
from dataclasses import dataclass

import structlog

from app.analysis import prompts
from app.analysis.llm import BudgetExceeded, LLMClient
from app.config import settings
from app.models.schemas import StoryAnalysis, StoryClusterIn

log = structlog.get_logger(__name__)


@dataclass
class AnalysisOutcome:
    cluster: StoryClusterIn
    analysis: StoryAnalysis | None
    error: str | None = None
    tokens_in: int = 0
    tokens_out: int = 0
    model: str = ""


async def analyze_cluster(client: LLMClient, cluster: StoryClusterIn,
                          bodies: dict[str, str]) -> AnalysisOutcome:
    user = prompts.build_analysis_user_prompt(cluster, bodies)
    try:
        result = await client.complete_json(
            system=prompts.SYSTEM_ANALYSIS,
            user=user,
            schema=StoryAnalysis,
            model=settings.llm_model_analysis,
            max_tokens=3000,
            effort="low",      # 36 of these a day; depth belongs in the deep dive
            purpose="analysis",
        )
    except BudgetExceeded:
        raise
    except Exception as exc:
        log.warning("analyzer.failed", cluster=cluster.key, error=str(exc)[:300])
        return AnalysisOutcome(cluster=cluster, analysis=None, error=str(exc)[:500])

    analysis = result.data
    # The model occasionally echoes a stale key/category; the pipeline is authoritative.
    analysis = analysis.model_copy(update={"cluster_key": cluster.key, "category": cluster.category})
    return AnalysisOutcome(cluster=cluster, analysis=analysis, tokens_in=result.tokens_in,
                           tokens_out=result.tokens_out, model=result.model)


async def analyze_all(client: LLMClient, clusters: list[StoryClusterIn],
                      bodies: dict[str, str]) -> list[AnalysisOutcome]:
    """Concurrency is bounded inside the client; failures are isolated per cluster."""
    tasks = [analyze_cluster(client, c, bodies) for c in clusters]
    outcomes: list[AnalysisOutcome] = []
    for coro in asyncio.as_completed(tasks):
        try:
            outcomes.append(await coro)
        except BudgetExceeded as exc:
            log.error("analyzer.budget_exceeded", error=str(exc))
            break
    ok = sum(1 for o in outcomes if o.analysis)
    log.info("analyzer.done", requested=len(clusters), analysed=ok, failed=len(outcomes) - ok)
    return outcomes

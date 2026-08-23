"""Phase 4: one long-form deep dive per day, on the story that matters most."""
from __future__ import annotations

import structlog

from app.analysis import prompts
from app.analysis.democracy import democracy_score
from app.analysis.llm import LLMClient
from app.config import settings
from app.models.schemas import DeepDive, DigestItem, StoryClusterIn

log = structlog.get_logger(__name__)


def pick_deep_dive(items: list[DigestItem]) -> DigestItem | None:
    """Highest democratic stakes, tie-broken by selection score. A day with no
    democratically relevant story gets no deep dive rather than a filler one."""
    candidates = [i for i in items if i.analysis.democracy.relevant]
    if not candidates:
        return None
    best = max(candidates, key=lambda i: (democracy_score(i.analysis), i.score.total))
    return best if democracy_score(best.analysis) >= 0.35 else None


async def generate_deep_dive(client: LLMClient, item: DigestItem, cluster: StoryClusterIn,
                             bodies: dict[str, str],
                             prior_context: list[dict] | None = None) -> DeepDive | None:
    user = prompts.build_deepdive_user_prompt(cluster, item.analysis, bodies, prior_context)
    embed_schema = not getattr(client, "enforces_schema", False)
    try:
        result = await client.complete_json(
            system=prompts.deepdive_system(include_schema=embed_schema),
            user=user,
            schema=DeepDive,
            model=settings.llm_model_deepdive,
            max_tokens=8000,
            effort="high",     # one a day, and the one people actually read
            purpose="deepdive",
        )
    except Exception as exc:
        log.warning("deepdive.failed", cluster=cluster.key, error=str(exc)[:300])
        return None

    dd = result.data.model_copy(update={"cluster_key": cluster.key})
    dd = _normalize_probabilities(dd)
    log.info("deepdive.done", cluster=cluster.key, tokens_out=result.tokens_out)
    return dd


def _normalize_probabilities(dd: DeepDive) -> DeepDive:
    """Scenario probabilities should sum to ~1. Rescale quietly rather than reject."""
    total = sum(s.probability for s in dd.scenarios)
    if total <= 0 or abs(total - 1.0) <= 0.15:
        return dd
    scaled = [s.model_copy(update={"probability": round(min(s.probability / total, 1.0), 3)})
              for s in dd.scenarios]
    return dd.model_copy(update={"scenarios": scaled})

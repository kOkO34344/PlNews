"""Central configuration. Everything tunable lives here or in .env."""
from __future__ import annotations

from functools import lru_cache
from pathlib import Path
from zoneinfo import ZoneInfo

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    app_env: str = "dev"
    database_url: str = "sqlite:///./data/plnews.db"
    timezone: str = "Europe/Sofia"
    digest_hour: int = 7

    # LLM
    anthropic_api_key: str = ""
    llm_model_analysis: str = "claude-sonnet-5"
    llm_model_deepdive: str = "claude-opus-5"
    llm_max_concurrency: int = 4
    llm_daily_token_budget: int = 2_000_000

    # delivery
    telegram_bot_token: str = ""
    telegram_allowed_chat_ids: str = ""
    obsidian_vault_path: Path = Path("./data/obsidian")
    api_key: str = "change-me"

    # ingestion
    ingest_lookback_hours: int = 30
    max_articles_per_source: int = 40
    http_user_agent: str = "PlNewsBot/0.1"

    # selection weights (see app/selection/selector.py)
    w_democracy: float = 0.30
    w_impact: float = 0.25
    w_novelty: float = 0.20
    w_credibility: float = 0.15
    w_personal: float = 0.10

    @field_validator("obsidian_vault_path", mode="before")
    @classmethod
    def _expand(cls, v: str | Path) -> Path:
        return Path(str(v)).expanduser()

    @property
    def tz(self) -> ZoneInfo:
        return ZoneInfo(self.timezone)

    @property
    def allowed_chat_ids(self) -> set[int]:
        raw = self.telegram_allowed_chat_ids or ""
        return {int(x) for x in raw.replace(" ", "").split(",") if x}


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()

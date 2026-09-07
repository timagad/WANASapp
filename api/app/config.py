"""Runtime configuration. Every value has a default that works offline."""
from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    app_name: str = "WANAS API"
    environment: str = "development"

    database_url: str = "postgresql+psycopg://wanas:wanas@localhost:5432/wanas"
    redis_url: str = "redis://localhost:6379/0"

    # Conversational LLM. Blank key => the offline grounded provider.
    anthropic_api_key: str = ""
    wanas_llm_model: str = "claude-sonnet-5"
    llm_timeout_seconds: float = 30.0
    llm_max_tokens: int = 900

    wanas_secret_key: str = "dev-only-insecure-key-change-me"
    access_token_minutes: int = 30
    refresh_token_days: int = 30

    # Retrieval
    embedding_dim: int = 384
    retrieval_top_k: int = 6
    # Fused score below which we refuse to answer rather than guess (AC-1.2).
    relevance_floor: float = 0.08

    # Cost control (NFR-7)
    answer_cache_seconds: int = 60 * 60 * 12
    free_daily_ai_calls: int = 40

    # Privacy: smallest cohort the institutional dashboard will ever expose (AC-7.1).
    min_cohort: int = 25

    cors_origins: str = "http://localhost:3000,http://127.0.0.1:3000"

    @property
    def llm_enabled(self) -> bool:
        return bool(self.anthropic_api_key.strip())

    @property
    def cors_list(self) -> list[str]:
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()

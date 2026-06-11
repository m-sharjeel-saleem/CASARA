"""Typed settings, loaded from the environment. Secrets live only here."""
from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    # LLM
    gemini_api_key: str = ""
    model_reasoning: str = "gemini-2.5-pro"
    model_fast: str = "gemini-2.5-flash"

    # GitHub (PAT mode)
    github_token: str = ""
    github_webhook_secret: str = ""

    # Policy
    risk_gate_threshold: float = 7.0

    # App
    database_path: str = "casara.db"
    cors_origins: str = "http://localhost:3000"

    @property
    def cors_origin_list(self) -> list[str]:
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]


@lru_cache
def get_settings() -> Settings:
    return Settings()

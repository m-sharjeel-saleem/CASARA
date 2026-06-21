"""Typed settings, loaded from the environment. Secrets live only here."""
from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    # LLM
    gemini_api_key: str = ""
    model_reasoning: str = "gemini-2.5-pro"
    model_fast: str = "gemini-2.5-flash"

    # GitHub App (multi-tenant, installable). Falls back to PAT mode if unset.
    github_app_id: str = ""
    github_app_private_key: str = ""       # PEM contents (supports \n-escaped single-line env)
    github_app_client_id: str = ""
    github_app_client_secret: str = ""
    github_app_slug: str = ""              # for the "Install" URL: github.com/apps/<slug>

    # GitHub (legacy PAT mode — still works for local/dev and single-repo use)
    github_token: str = ""
    github_webhook_secret: str = ""

    @property
    def github_app_enabled(self) -> bool:
        return bool(self.github_app_id and self.github_app_private_key)

    @property
    def private_key_pem(self) -> str:
        # Allow the key to be stored as a single line with literal \n (common in PaaS env UIs).
        return self.github_app_private_key.replace("\\n", "\n")

    # Policy
    risk_gate_threshold: float = 7.0
    max_autofixes: int = 3  # max one-click suggested fixes posted per PR (bounds LLM cost)

    # App
    database_path: str = "casara.db"
    cors_origins: str = "http://localhost:3000"

    @property
    def cors_origin_list(self) -> list[str]:
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]


@lru_cache
def get_settings() -> Settings:
    return Settings()

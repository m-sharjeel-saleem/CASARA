"""Typed settings, loaded from the environment. Secrets live only here."""
from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    # LLM
    gemini_api_key: str = ""
    model_reasoning: str = "gemini-2.5-pro"
    model_fast: str = "gemini-2.5-flash"
    # Min seconds between Gemini calls (free-tier pacing). 0 disables. ~6.5s ≈ under 10 RPM.
    gemini_min_interval_s: float = 6.5

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

    # Billing: free-tier monthly review cap per installation. 0 = unlimited (no cap enforced).
    free_monthly_reviews: int = 0

    # Storage. SQLite by default (local/dev). Set SUPABASE_URL + SUPABASE_SERVICE_KEY
    # to switch the store backend to Supabase (hosted, multi-tenant) automatically.
    database_path: str = "casara.db"
    supabase_url: str = ""
    supabase_service_key: str = ""        # service-role key — server-side only, bypasses RLS
    supabase_anon_key: str = ""           # public anon key — used by the frontend
    cors_origins: str = "http://localhost:3000"

    @property
    def use_supabase(self) -> bool:
        return bool(self.supabase_url and self.supabase_service_key)

    @property
    def cors_origin_list(self) -> list[str]:
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]


@lru_cache
def get_settings() -> Settings:
    return Settings()

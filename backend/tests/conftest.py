"""Test fixtures — keyless, isolated SQLite, no network."""
import pytest

from app.config import get_settings


@pytest.fixture(autouse=True)
def isolated_env(monkeypatch, tmp_path):
    monkeypatch.setenv("GEMINI_API_KEY", "")
    monkeypatch.setenv("GEMINI_2", "")
    monkeypatch.setenv("GEMINI_API_KEY_3", "")
    monkeypatch.setenv("GROQ_API_KEY_1", "")
    monkeypatch.setenv("GITHUB_TOKEN", "")
    monkeypatch.setenv("GITHUB_WEBHOOK_SECRET", "")
    monkeypatch.setenv("DATABASE_PATH", str(tmp_path / "test.db"))
    # Force the local SQLite backend so tests never touch a real Supabase project,
    # even when the developer's .env has live SUPABASE_* credentials set.
    monkeypatch.setenv("SUPABASE_URL", "")
    monkeypatch.setenv("SUPABASE_SERVICE_KEY", "")
    monkeypatch.setenv("FREE_MONTHLY_REVIEWS", "0")
    get_settings.cache_clear()
    from app.db import store
    store.init_db()
    yield
    get_settings.cache_clear()

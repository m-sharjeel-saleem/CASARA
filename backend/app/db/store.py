"""Storage dispatcher.

One stable interface; the backend is chosen at runtime: Supabase when configured
(SUPABASE_URL + SUPABASE_SERVICE_KEY), else local SQLite (default for dev/tests).
This lets the whole app stay backend-agnostic — callers just use `store.save_review(...)`.
"""
from app.config import get_settings
from app.db import sqlite_store, supabase_store
from app.models import Review


def _backend():
    return supabase_store if get_settings().use_supabase else sqlite_store


def init_db() -> None:
    _backend().init_db()


def save_review(review: Review) -> None:
    _backend().save_review(review)


def get_review(review_id: str) -> Review | None:
    return _backend().get_review(review_id)


def list_reviews(limit: int = 50, installation_id: int | None = None) -> list[Review]:
    b = _backend()
    # sqlite_store.list_reviews predates the installation filter; pass through when supported.
    if b is supabase_store:
        return b.list_reviews(limit, installation_id=installation_id)
    return b.list_reviews(limit)


def stats(installation_id: int | None = None) -> dict:
    b = _backend()
    if b is supabase_store:
        return b.stats(installation_id=installation_id)
    return b.stats()


def upsert_installation(inst_id: int, account: str, account_type: str,
                        repo_count: int, created_at: str) -> None:
    _backend().upsert_installation(inst_id, account, account_type, repo_count, created_at)


def set_installation_suspended(inst_id: int, suspended: bool) -> None:
    _backend().set_installation_suspended(inst_id, suspended)


def delete_installation(inst_id: int) -> None:
    _backend().delete_installation(inst_id)

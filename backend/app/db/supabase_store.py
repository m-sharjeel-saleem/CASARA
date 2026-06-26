"""Supabase (PostgREST) store — same interface as sqlite_store.

Server-side writes use the service-role key, which bypasses Row-Level Security; end-user
reads go through the API which applies RLS. We talk to PostgREST over httpx to avoid a
heavy SDK dependency. Selected only when SUPABASE_URL + SUPABASE_SERVICE_KEY are set.
"""
from __future__ import annotations

import logging

import httpx

from app.config import get_settings
from app.models import Review

log = logging.getLogger("casara.supabase")


def _rest() -> tuple[str, dict]:
    s = get_settings()
    base = f"{s.supabase_url.rstrip('/')}/rest/v1"
    headers = {
        "apikey": s.supabase_service_key,
        "Authorization": f"Bearer {s.supabase_service_key}",
        "Content-Type": "application/json",
    }
    return base, headers


def init_db() -> None:
    # Schema is managed by supabase/migrations/0001_init.sql (applied out-of-band).
    return None


def _review_payload(r: Review) -> dict:
    return {
        "id": r.id, "installation_id": r.installation_id, "repo": r.repo,
        "pr_number": r.pr_number, "pr_title": r.pr_title, "author": r.author,
        "head_sha": r.head_sha, "status": r.status, "risk_score": r.risk_score,
        "gated": r.gated, "summary": r.summary,
        "findings": [f.model_dump() for f in r.findings],
        "created_at": r.created_at, "completed_at": r.completed_at,
    }


def save_review(review: Review) -> None:
    base, headers = _rest()
    headers = {**headers, "Prefer": "resolution=merge-duplicates"}
    with httpx.Client(timeout=30) as c:
        r = c.post(f"{base}/reviews", headers=headers, json=_review_payload(review))
        if r.status_code >= 300:
            # Loud + raised: a silently-dropped persist is worse than a failed review.
            log.error("supabase save_review failed %s: %s", r.status_code, r.text[:300])
            raise RuntimeError(f"supabase save_review {r.status_code}: {r.text[:200]}")


# String columns are nullable in Postgres; the model wants "" not None.
_STR_FIELDS = ("pr_title", "author", "head_sha", "summary", "repo", "status")


def _to_review(row: dict) -> Review:
    findings = row.pop("findings", []) or []
    data = {k: row.get(k) for k in Review.model_fields if k != "findings"}
    for f in _STR_FIELDS:
        if data.get(f) is None:
            data[f] = ""
    if data.get("risk_score") is None:
        data["risk_score"] = 0.0
    return Review(**data, findings=findings)


def get_review(review_id: str) -> Review | None:
    base, headers = _rest()
    with httpx.Client(timeout=30) as c:
        r = c.get(f"{base}/reviews", headers=headers,
                  params={"id": f"eq.{review_id}", "select": "*", "limit": 1})
        rows = r.json() if r.status_code < 300 else []
    return _to_review(rows[0]) if rows else None


def list_reviews(limit: int = 50, installation_id: int | None = None) -> list[Review]:
    base, headers = _rest()
    params = {"select": "*", "order": "created_at.desc", "limit": str(limit)}
    if installation_id is not None:
        params["installation_id"] = f"eq.{installation_id}"
    with httpx.Client(timeout=30) as c:
        r = c.get(f"{base}/reviews", headers=headers, params=params)
        rows = r.json() if r.status_code < 300 else []
    return [_to_review(row) for row in rows]


def upsert_installation(inst_id: int, account: str, account_type: str,
                        repo_count: int, created_at: str) -> None:
    base, headers = _rest()
    headers = {**headers, "Prefer": "resolution=merge-duplicates"}
    with httpx.Client(timeout=30) as c:
        c.post(f"{base}/installations", headers=headers, json={
            "id": inst_id, "account": account, "account_type": account_type,
            "repo_count": repo_count, "created_at": created_at, "suspended": False,
        })


def set_installation_suspended(inst_id: int, suspended: bool) -> None:
    base, headers = _rest()
    with httpx.Client(timeout=30) as c:
        c.patch(f"{base}/installations", headers=headers,
                params={"id": f"eq.{inst_id}"}, json={"suspended": suspended})


def delete_installation(inst_id: int) -> None:
    base, headers = _rest()
    with httpx.Client(timeout=30) as c:
        c.delete(f"{base}/installations", headers=headers, params={"id": f"eq.{inst_id}"})


def get_usage(inst_id: int, period: str) -> int:
    base, headers = _rest()
    with httpx.Client(timeout=30) as c:
        r = c.get(f"{base}/usage_counters", headers=headers, params={
            "installation_id": f"eq.{inst_id}", "period": f"eq.{period}",
            "select": "reviews_run", "limit": 1,
        })
        rows = r.json() if r.status_code < 300 else []
    return rows[0]["reviews_run"] if rows else 0


def incr_usage(inst_id: int, period: str) -> int:
    # Read-modify-write; fine at our volume (one increment per review).
    current = get_usage(inst_id, period)
    base, headers = _rest()
    headers = {**headers, "Prefer": "resolution=merge-duplicates"}
    with httpx.Client(timeout=30) as c:
        c.post(f"{base}/usage_counters", headers=headers, json={
            "installation_id": inst_id, "period": period, "reviews_run": current + 1,
        })
    return current + 1


def list_installations() -> list[dict]:
    base, headers = _rest()
    with httpx.Client(timeout=30) as c:
        r = c.get(f"{base}/installations", headers=headers,
                  params={"select": "*", "order": "created_at.desc"})
        return r.json() if r.status_code < 300 else []


def get_config(inst_id: int) -> dict:
    base, headers = _rest()
    with httpx.Client(timeout=30) as c:
        r = c.get(f"{base}/configs", headers=headers,
                  params={"installation_id": f"eq.{inst_id}", "select": "data", "limit": 1})
        rows = r.json() if r.status_code < 300 else []
    return (rows[0].get("data") or {}) if rows else {}


def set_config(inst_id: int, data: dict, updated_at: str) -> None:
    base, headers = _rest()
    headers = {**headers, "Prefer": "resolution=merge-duplicates"}
    with httpx.Client(timeout=30) as c:
        r = c.post(f"{base}/configs", headers=headers,
                   json={"installation_id": inst_id, "data": data, "updated_at": updated_at})
        if r.status_code >= 300:
            log.error("supabase set_config failed %s: %s", r.status_code, r.text[:200])
            raise RuntimeError(f"set_config {r.status_code}")


def stats(installation_id: int | None = None) -> dict:
    reviews = list_reviews(limit=1000, installation_id=installation_id)
    done = [r for r in reviews if r.status == "completed"]
    total = len(done)
    gated = sum(1 for r in done if r.gated)
    avg = round(sum(r.risk_score for r in done) / total, 2) if total else 0
    findings = sum(len(r.findings) for r in done)
    return {"total_reviews": total, "gated_count": gated,
            "avg_risk": avg, "total_findings": findings}

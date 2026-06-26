"""Dashboard API: reviews, stats, live SSE feed, and a manual trigger."""
import asyncio

from fastapi import APIRouter, BackgroundTasks, HTTPException
from pydantic import BaseModel, Field
from sse_starlette.sse import EventSourceResponse

import re

from app.core import events
from app.db import store
from app.services import gh_app, github
from app.services.review import run_review

router = APIRouter(prefix="/api", tags=["dashboard"])


@router.get("/install")
def install_url() -> dict:
    """Where the 'Install on GitHub' button sends a customer.

    Returns the public GitHub App install URL when the App is configured, so the
    frontend can render a real install button (the self-serve entry point).
    """
    from app.config import get_settings
    s = get_settings()
    if s.github_app_slug:
        return {"configured": True,
                "url": f"https://github.com/apps/{s.github_app_slug}/installations/new"}
    return {"configured": False, "url": None}


@router.get("/stats")
def get_stats() -> dict:
    return store.stats()


@router.get("/reviews")
def get_reviews(limit: int = 50) -> list:
    return [r.model_dump() for r in store.list_reviews(limit)]


@router.get("/reviews/{review_id}")
def get_review(review_id: str) -> dict:
    review = store.get_review(review_id)
    if not review:
        raise HTTPException(status_code=404, detail="review not found")
    return review.model_dump()


class RunRequest(BaseModel):
    repo: str = Field(..., examples=["owner/name", "https://github.com/owner/name/pull/8"])
    pr_number: int | None = Field(None, examples=[8])


_PR_URL = re.compile(r"github\.com/([^/]+/[^/]+)/pull/(\d+)")


def _normalize(repo: str, pr_number: int | None) -> tuple[str, int]:
    """Accept either (owner/repo, pr_number) or a full PR URL pasted into `repo`."""
    m = _PR_URL.search(repo)
    if m:
        return m.group(1), int(m.group(2))
    repo = repo.strip().removeprefix("https://github.com/").removeprefix("github.com/").strip("/")
    if pr_number is None:
        raise HTTPException(status_code=422, detail="Provide a PR number, or paste the full PR URL.")
    return repo, pr_number


@router.post("/review/run")
def trigger_review(req: RunRequest, background: BackgroundTasks) -> dict:
    """Manually trigger a review for a PR (useful without webhooks).

    Resolves the GitHub App installation for the repo so it works on private repos
    the App is installed on; falls back to PAT/none otherwise.
    """
    repo, pr_number = _normalize(req.repo, req.pr_number)
    installation_id = gh_app.installation_for_repo(repo)
    try:
        pr = github.get_pr(repo, pr_number, installation_id)
    except Exception as e:  # noqa: BLE001
        hint = (" — make sure CASARA is installed on this repo (Install on GitHub)."
                if installation_id is None else "")
        raise HTTPException(status_code=400, detail=f"cannot fetch PR: {e}{hint}") from e
    background.add_task(
        run_review,
        repo=repo, pr_number=pr_number, pr_title=pr.get("title", ""),
        author=pr.get("user", {}).get("login", ""),
        head_sha=pr.get("head", {}).get("sha", ""),
        installation_id=installation_id,
    )
    return {"status": "accepted", "repo": repo, "pr": pr_number}


@router.get("/events")
async def event_stream():
    """Server-Sent Events feed of review lifecycle events for the dashboard."""
    async def gen():
        q = events.subscribe()
        try:
            while True:
                try:
                    msg = await asyncio.wait_for(q.get(), timeout=20)
                    yield msg
                except asyncio.TimeoutError:
                    yield {"event": "ping", "data": "{}"}
        finally:
            events.unsubscribe(q)

    return EventSourceResponse(gen())

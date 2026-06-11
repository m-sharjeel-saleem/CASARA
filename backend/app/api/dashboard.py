"""Dashboard API: reviews, stats, live SSE feed, and a manual trigger."""
import asyncio

from fastapi import APIRouter, BackgroundTasks, HTTPException
from pydantic import BaseModel, Field
from sse_starlette.sse import EventSourceResponse

from app.core import events
from app.db import store
from app.services import github
from app.services.review import run_review

router = APIRouter(prefix="/api", tags=["dashboard"])


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
    repo: str = Field(..., examples=["owner/name"])
    pr_number: int = Field(..., examples=[1])


@router.post("/review/run")
def trigger_review(req: RunRequest, background: BackgroundTasks) -> dict:
    """Manually trigger a review for a PR (useful without webhooks)."""
    try:
        pr = github.get_pr(req.repo, req.pr_number)
    except Exception as e:  # noqa: BLE001
        raise HTTPException(status_code=400, detail=f"cannot fetch PR: {e}") from e
    background.add_task(
        run_review,
        repo=req.repo, pr_number=req.pr_number, pr_title=pr.get("title", ""),
        author=pr.get("user", {}).get("login", ""),
        head_sha=pr.get("head", {}).get("sha", ""),
    )
    return {"status": "accepted", "repo": req.repo, "pr": req.pr_number}


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

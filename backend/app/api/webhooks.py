"""GitHub webhook receiver — verifies, then processes the PR in the background."""
import logging

from fastapi import APIRouter, BackgroundTasks, Header, HTTPException, Request

from app.core.security import verify_signature
from app.services.review import run_review

log = logging.getLogger("casara.webhooks")
router = APIRouter(tags=["webhooks"])

_TRIGGER_ACTIONS = {"opened", "synchronize", "reopened"}


@router.post("/webhooks/github")
async def github_webhook(
    request: Request,
    background: BackgroundTasks,
    x_github_event: str = Header(default=""),
    x_hub_signature_256: str | None = Header(default=None),
):
    body = await request.body()
    if not verify_signature(body, x_hub_signature_256):
        raise HTTPException(status_code=401, detail="invalid signature")

    if x_github_event != "pull_request":
        return {"status": "ignored", "reason": f"event {x_github_event!r} not handled"}

    payload = await request.json()
    if payload.get("action") not in _TRIGGER_ACTIONS:
        return {"status": "ignored", "reason": f"action {payload.get('action')!r}"}

    pr = payload["pull_request"]
    background.add_task(
        run_review,
        repo=payload["repository"]["full_name"],
        pr_number=pr["number"],
        pr_title=pr.get("title", ""),
        author=pr.get("user", {}).get("login", ""),
        head_sha=pr.get("head", {}).get("sha", ""),
    )
    return {"status": "accepted", "pr": pr["number"]}

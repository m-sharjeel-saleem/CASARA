"""GitHub webhook receiver — verifies, then processes the PR in the background."""
import logging

from fastapi import APIRouter, BackgroundTasks, Header, HTTPException, Request

from app.core.security import verify_signature
from app.services import github
from app.services.review import run_review
from app.services.tenants import on_installation

log = logging.getLogger("casara.webhooks")
router = APIRouter(tags=["webhooks"])

_TRIGGER_ACTIONS = {"opened", "synchronize", "reopened"}
_REVIEW_COMMANDS = ("@casara review", "@casara-security review", "/casara review")


def _handle_command(payload: dict, background) -> dict:
    """Run a review when someone comments a command on a pull request."""
    if payload.get("action") not in ("created", "edited"):
        return {"status": "ignored", "reason": "comment not created"}
    if "pull_request" not in payload.get("issue", {}):
        return {"status": "ignored", "reason": "comment not on a PR"}
    body = (payload.get("comment", {}).get("body") or "").lower()
    if not any(cmd in body for cmd in _REVIEW_COMMANDS):
        return {"status": "ignored", "reason": "no recognised command"}

    repo = payload["repository"]["full_name"]
    pr_number = payload["issue"]["number"]
    installation_id = payload.get("installation", {}).get("id")
    try:
        pr = github.get_pr(repo, pr_number, installation_id)
    except Exception as e:  # noqa: BLE001
        return {"status": "error", "reason": f"cannot fetch PR: {e}"}
    background.add_task(
        run_review, repo=repo, pr_number=pr_number, pr_title=pr.get("title", ""),
        author=pr.get("user", {}).get("login", ""),
        head_sha=pr.get("head", {}).get("sha", ""), installation_id=installation_id,
    )
    return {"status": "accepted", "command": "review", "pr": pr_number}


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

    payload = await request.json()

    # App lifecycle events: record/forget the installation (the tenant).
    if x_github_event in ("installation", "installation_repositories"):
        inst = payload.get("installation", {})
        on_installation(payload.get("action", ""), inst)
        return {"status": "ok", "installation": inst.get("id")}

    # PR chat slash-commands: "@casara review" on a pull-request comment.
    if x_github_event == "issue_comment":
        return _handle_command(payload, background)

    if x_github_event != "pull_request":
        return {"status": "ignored", "reason": f"event {x_github_event!r} not handled"}

    if payload.get("action") not in _TRIGGER_ACTIONS:
        return {"status": "ignored", "reason": f"action {payload.get('action')!r}"}

    pr = payload["pull_request"]
    installation_id = payload.get("installation", {}).get("id")
    background.add_task(
        run_review,
        repo=payload["repository"]["full_name"],
        pr_number=pr["number"],
        pr_title=pr.get("title", ""),
        author=pr.get("user", {}).get("login", ""),
        head_sha=pr.get("head", {}).get("sha", ""),
        installation_id=installation_id,
    )
    return {"status": "accepted", "pr": pr["number"]}

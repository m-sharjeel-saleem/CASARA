"""GitHub integration (Personal Access Token mode — no GitHub App needed).

Fetches PR metadata, changed files, and diff; posts a single consolidated review
comment; and sets a commit status used for merge gating via branch protection.
All calls no-op gracefully when no token is configured.
"""
import base64
import logging

import httpx

from app.config import get_settings

log = logging.getLogger("casara.github")
_API = "https://api.github.com"


def _headers(diff: bool = False) -> dict[str, str]:
    h = {
        "Accept": "application/vnd.github.v3.diff" if diff else "application/vnd.github+json",
        "X-GitHub-Api-Version": "2022-11-28",
    }
    token = get_settings().github_token
    if token and not token.startswith("ghp_xxxx"):
        h["Authorization"] = f"Bearer {token}"
    return h


def _enabled() -> bool:
    token = get_settings().github_token
    return bool(token) and not token.startswith("ghp_xxxx")


def get_pr(repo: str, pr_number: int) -> dict:
    with httpx.Client(timeout=30) as c:
        r = c.get(f"{_API}/repos/{repo}/pulls/{pr_number}", headers=_headers())
        r.raise_for_status()
        return r.json()


def get_diff(repo: str, pr_number: int) -> str:
    with httpx.Client(timeout=30) as c:
        r = c.get(f"{_API}/repos/{repo}/pulls/{pr_number}", headers=_headers(diff=True))
        r.raise_for_status()
        return r.text


def changed_files(repo: str, pr_number: int) -> list[str]:
    files: list[str] = []
    with httpx.Client(timeout=30) as c:
        r = c.get(f"{_API}/repos/{repo}/pulls/{pr_number}/files",
                  params={"per_page": 100}, headers=_headers())
        r.raise_for_status()
        files = [f["filename"] for f in r.json() if f.get("status") != "removed"]
    return files


def fetch_file(repo: str, path: str, ref: str) -> str | None:
    try:
        with httpx.Client(timeout=30) as c:
            r = c.get(f"{_API}/repos/{repo}/contents/{path}",
                      params={"ref": ref}, headers=_headers())
            r.raise_for_status()
            data = r.json()
            if data.get("encoding") == "base64":
                return base64.b64decode(data["content"]).decode("utf-8", errors="replace")
    except (httpx.HTTPError, ValueError):
        return None
    return None


def post_comment(repo: str, pr_number: int, body: str) -> bool:
    if not _enabled():
        log.info("GitHub disabled — skipping comment post")
        return False
    with httpx.Client(timeout=30) as c:
        r = c.post(f"{_API}/repos/{repo}/issues/{pr_number}/comments",
                   headers=_headers(), json={"body": body})
        return r.status_code < 300


def post_suggestion(
    repo: str, pr_number: int, commit_id: str, path: str,
    start_line: int, end_line: int, replacement: str, body: str,
) -> bool:
    """Post an inline review comment with a GitHub 'suggestion' block.

    GitHub renders ```suggestion blocks with an 'Apply suggestion' button, so the PR
    author can accept the fix in one click. Single-line vs multi-line uses different
    fields per the GitHub review-comments API.
    """
    if not _enabled() or not commit_id:
        return False
    suggestion = "```suggestion\n" + replacement + "\n```"
    payload: dict = {
        "body": f"{body}\n\n{suggestion}",
        "commit_id": commit_id,
        "path": path,
        "line": end_line,
        "side": "RIGHT",
    }
    if end_line > start_line:
        payload["start_line"] = start_line
        payload["start_side"] = "RIGHT"
    with httpx.Client(timeout=30) as c:
        r = c.post(f"{_API}/repos/{repo}/pulls/{pr_number}/comments",
                   headers=_headers(), json=payload)
        if r.status_code >= 300:
            log.warning("suggestion post failed %s: %s", r.status_code, r.text[:200])
        return r.status_code < 300


def set_status(repo: str, sha: str, *, gated: bool, description: str) -> bool:
    """Set a commit status used as a required check for merge gating."""
    if not _enabled() or not sha:
        return False
    with httpx.Client(timeout=30) as c:
        r = c.post(
            f"{_API}/repos/{repo}/statuses/{sha}",
            headers=_headers(),
            json={
                "state": "failure" if gated else "success",
                "context": "casara/security-review",
                "description": description[:140],
            },
        )
        return r.status_code < 300

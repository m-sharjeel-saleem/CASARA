"""GitHub App authentication — what makes CASARA installable & multi-tenant.

A Personal Access Token is one user's credential. A GitHub *App* is installed per
org/repo; CASARA authenticates AS each installation:

  1. Sign a short-lived JWT with the App's private key (RS256) — proves we are the App.
  2. Exchange that JWT for an *installation access token* scoped to one customer's repos.
  3. Use that token for API calls on that installation's behalf.

Installation tokens last ~1h, so we cache them per-installation until just before expiry.
"""
from __future__ import annotations

import logging
import time

import httpx
import jwt

from app.config import get_settings

log = logging.getLogger("casara.gh_app")
_API = "https://api.github.com"

# installation_id -> (token, expires_at_epoch)
_token_cache: dict[int, tuple[str, float]] = {}
_SKEW = 60  # refresh this many seconds before actual expiry


def _app_jwt() -> str:
    """A short-lived JWT identifying the App itself (not any installation)."""
    s = get_settings()
    now = int(time.time())
    payload = {"iat": now - 30, "exp": now + 540, "iss": s.github_app_id}  # 9-min max
    return jwt.encode(payload, s.private_key_pem, algorithm="RS256")


def installation_token(installation_id: int) -> str | None:
    """Return a cached or freshly-minted installation access token, or None on failure."""
    cached = _token_cache.get(installation_id)
    if cached and cached[1] - _SKEW > time.time():
        return cached[0]

    if not get_settings().github_app_enabled:
        return None
    try:
        with httpx.Client(timeout=30) as c:
            r = c.post(
                f"{_API}/app/installations/{installation_id}/access_tokens",
                headers={
                    "Authorization": f"Bearer {_app_jwt()}",
                    "Accept": "application/vnd.github+json",
                    "X-GitHub-Api-Version": "2022-11-28",
                },
            )
            r.raise_for_status()
            data = r.json()
    except (httpx.HTTPError, ValueError) as e:
        log.warning("installation token fetch failed for %s: %s", installation_id, e)
        return None

    token = data["token"]
    # expires_at is ISO; we don't need exact parsing — assume ~1h and cache conservatively.
    _token_cache[installation_id] = (token, time.time() + 3000)
    return token


def list_installations() -> list[dict]:
    """All installations of this App (used to map installs to tenants)."""
    if not get_settings().github_app_enabled:
        return []
    try:
        with httpx.Client(timeout=30) as c:
            r = c.get(
                f"{_API}/app/installations",
                headers={
                    "Authorization": f"Bearer {_app_jwt()}",
                    "Accept": "application/vnd.github+json",
                    "X-GitHub-Api-Version": "2022-11-28",
                },
            )
            r.raise_for_status()
            return r.json()
    except (httpx.HTTPError, ValueError) as e:
        log.warning("list installations failed: %s", e)
        return []

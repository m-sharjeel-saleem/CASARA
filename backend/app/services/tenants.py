"""Tenant lifecycle — maps GitHub App installations to customers.

For launch this records installations in the local store. In Phase 3 this is where the
Supabase-backed account/organization linkage will live (the function signatures stay the
same so the webhook never needs to change).
"""
import logging
from datetime import datetime, timezone

from app.db import store

log = logging.getLogger("casara.tenants")


def on_installation(action: str, installation: dict) -> None:
    """Handle GitHub App 'installation' / 'installation_repositories' webhook events."""
    inst_id = installation.get("id")
    if not inst_id:
        return
    account = installation.get("account", {})

    if action in ("created", "added", "new_permissions_accepted", "unsuspend"):
        store.upsert_installation(
            inst_id=inst_id,
            account=account.get("login", ""),
            account_type=account.get("type", ""),
            repo_count=installation.get("repository_selection") == "all"
                       and -1 or len(installation.get("repositories", []) or []),
            created_at=datetime.now(timezone.utc).isoformat(),
        )
        log.info("installation %s active for %s", inst_id, account.get("login"))
    elif action == "suspend":
        store.set_installation_suspended(inst_id, True)
    elif action in ("deleted", "removed"):
        store.delete_installation(inst_id)
        log.info("installation %s removed", inst_id)

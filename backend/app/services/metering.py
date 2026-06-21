"""Usage metering + free-tier cap.

Counts reviews per installation per calendar month. When a free-tier installation exceeds
`FREE_MONTHLY_REVIEWS`, the pipeline posts an upgrade notice instead of running a full
(cost-incurring) review. This is the data layer billing will plug into (Phase 4 / Stripe);
the Stripe checkout itself is the only remaining piece and needs your Stripe account.
"""
from datetime import datetime, timezone

from app.config import get_settings
from app.db import store


def current_period() -> str:
    now = datetime.now(timezone.utc)
    return f"{now.year:04d}-{now.month:02d}"


def record_review(installation_id: int | None) -> int:
    """Increment this installation's monthly counter; returns the new count (0 in PAT mode)."""
    if not installation_id:
        return 0
    return store.incr_usage(installation_id, current_period())


def over_free_limit(installation_id: int | None) -> bool:
    """True if a free-tier installation has used up its monthly allowance."""
    cap = get_settings().free_monthly_reviews
    if cap <= 0 or not installation_id:
        return False  # unlimited / not metered (e.g. PAT mode or cap disabled)
    return store.get_usage(installation_id, current_period()) >= cap

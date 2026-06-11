"""In-process pub/sub for dashboard Server-Sent Events.

Deliberately in-process (asyncio queues) rather than Redis pub/sub — for a
single-instance daily-review tool this removes an external dependency. Swap for
Redis only if you scale to multiple backend instances.
"""
import asyncio
import json

_subscribers: set[asyncio.Queue] = set()


def subscribe() -> asyncio.Queue:
    q: asyncio.Queue = asyncio.Queue(maxsize=100)
    _subscribers.add(q)
    return q


def unsubscribe(q: asyncio.Queue) -> None:
    _subscribers.discard(q)


def publish(event: str, data: dict) -> None:
    """Fan out an event to all connected dashboard clients (non-blocking)."""
    payload = {"event": event, "data": json.dumps(data)}
    for q in list(_subscribers):
        try:
            q.put_nowait(payload)
        except asyncio.QueueFull:
            pass  # slow client; drop rather than block the pipeline

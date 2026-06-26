"""Google Gemini wrapper (REST via httpx).

Degrades gracefully: with no GEMINI_API_KEY, returns a stub so the pipeline runs
keyless. Key is sent as a header (never in the URL) and transient errors retry.
"""
import json
import threading
import time
from dataclasses import dataclass

import httpx

from app.config import get_settings

_BASE = "https://generativelanguage.googleapis.com/v1beta"
_RETRY_STATUS = {429, 500, 502, 503, 504}
_MAX_ATTEMPTS = 3

# Process-wide pacing. The free Gemini tier limits requests-per-minute; the review
# pipeline fires several calls (agents in parallel + critic + summary + fixes), so we
# serialize them through a minimum interval to stay under the cap. Concurrency for the
# orchestrator is preserved — threads just queue here.
_pace_lock = threading.Lock()
_last_call = [0.0]
_degraded = [0]  # count of calls that failed (quota/transient) since the last reset


def reset_degraded() -> None:
    _degraded[0] = 0


def degraded_count() -> int:
    return _degraded[0]


@dataclass
class LLMResult:
    text: str
    stub: bool = False


def _throttle(interval: float) -> None:
    if interval <= 0:
        return
    with _pace_lock:
        wait = interval - (time.monotonic() - _last_call[0])
        if wait > 0:
            time.sleep(wait)
        _last_call[0] = time.monotonic()


def _request(path: str, body: dict) -> dict:
    """POST to Gemini, rotating across configured keys when one hits its quota.

    Each key gets a couple of attempts; a 429 (quota) moves on to the next key so a
    review keeps working when the first key's daily free quota is exhausted.
    """
    settings = get_settings()
    keys = settings.gemini_keys
    interval = settings.gemini_min_interval_s
    last: Exception | None = None
    for ki, key in enumerate(keys):
        headers = {"x-goog-api-key": key, "Content-Type": "application/json"}
        for attempt in range(_MAX_ATTEMPTS):
            _throttle(interval)
            try:
                r = httpx.post(f"{_BASE}/{path}", headers=headers, json=body, timeout=90)
                if r.status_code == 429:
                    last = RuntimeError("quota 429")
                    break  # this key is rate/quota limited — switch to the next key
                if r.status_code in _RETRY_STATUS:
                    last = RuntimeError(f"transient {r.status_code}")
                else:
                    r.raise_for_status()
                    return r.json()
            except (httpx.TransportError, httpx.HTTPStatusError) as e:
                last = e
            if attempt < _MAX_ATTEMPTS - 1:
                time.sleep(min(8.0, 3.0 * (attempt + 1)))
    raise RuntimeError(f"Gemini request failed across {len(keys)} key(s): {last}")


def complete_json(system: str, prompt: str, *, model: str | None = None) -> object:
    """JSON-constrained completion. Returns parsed JSON, or None (no key / quota / parse fail)."""
    if not get_settings().gemini_keys:
        return None
    model = model or get_settings().model_fast
    body = {
        "contents": [{"parts": [{"text": prompt}]}],
        "systemInstruction": {"parts": [{"text": system}]},
        "generationConfig": {
            "response_mime_type": "application/json",
            # Disable "thinking" on Gemini 2.5 flash — review prompts don't need it, and it
            # roughly 5x's latency. Huge speed win for the multi-call review pipeline.
            "thinkingConfig": {"thinkingBudget": 0},
        },
    }
    try:
        data = _request(f"models/{model}:generateContent", body)
    except RuntimeError as e:
        # Quota/transient failure must NOT fail the whole review — the AI layer is
        # additive. Degrade to no AI findings; deterministic scanners still produce a review.
        import logging
        _degraded[0] += 1
        logging.getLogger("casara.llm").warning("LLM call degraded (no AI findings): %s", e)
        return None
    try:
        text = data["candidates"][0]["content"]["parts"][0]["text"]
        return json.loads(text)
    except (KeyError, IndexError, json.JSONDecodeError, TypeError):
        return None

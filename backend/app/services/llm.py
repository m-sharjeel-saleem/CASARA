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


@dataclass
class LLMResult:
    text: str
    stub: bool = False


def _key() -> str | None:
    k = get_settings().gemini_api_key
    return k if k and not k.startswith("AIzaSyxxxx") else None


def _throttle(interval: float) -> None:
    if interval <= 0:
        return
    with _pace_lock:
        wait = interval - (time.monotonic() - _last_call[0])
        if wait > 0:
            time.sleep(wait)
        _last_call[0] = time.monotonic()


def _request(path: str, key: str, body: dict) -> dict:
    headers = {"x-goog-api-key": key, "Content-Type": "application/json"}
    interval = get_settings().gemini_min_interval_s
    last: Exception | None = None
    for attempt in range(_MAX_ATTEMPTS):
        _throttle(interval)
        try:
            r = httpx.post(f"{_BASE}/{path}", headers=headers, json=body, timeout=90)
            if r.status_code in _RETRY_STATUS:
                last = RuntimeError(f"transient {r.status_code}")
            else:
                r.raise_for_status()
                return r.json()
        except (httpx.TransportError, httpx.HTTPStatusError) as e:
            last = e
        if attempt < _MAX_ATTEMPTS - 1:
            # Back off on 429 but fail fast enough not to hang the whole review.
            time.sleep(min(12.0, 4.0 * (attempt + 1)))
    raise RuntimeError(f"Gemini request failed after {_MAX_ATTEMPTS} attempts: {last}")


def complete_json(system: str, prompt: str, *, model: str | None = None) -> object:
    """JSON-constrained completion. Returns parsed JSON, or None (stub/parse fail)."""
    key = _key()
    if not key:
        return None
    model = model or get_settings().model_fast
    body = {
        "contents": [{"parts": [{"text": prompt}]}],
        "systemInstruction": {"parts": [{"text": system}]},
        "generationConfig": {"response_mime_type": "application/json"},
    }
    data = _request(f"models/{model}:generateContent", key, body)
    try:
        text = data["candidates"][0]["content"]["parts"][0]["text"]
        return json.loads(text)
    except (KeyError, IndexError, json.JSONDecodeError, TypeError):
        return None

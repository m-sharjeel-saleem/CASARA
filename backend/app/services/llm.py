"""Google Gemini wrapper (REST via httpx).

Degrades gracefully: with no GEMINI_API_KEY, returns a stub so the pipeline runs
keyless. Key is sent as a header (never in the URL) and transient errors retry.
"""
import json
import time
from dataclasses import dataclass

import httpx

from app.config import get_settings

_BASE = "https://generativelanguage.googleapis.com/v1beta"
_RETRY_STATUS = {429, 500, 502, 503, 504}
_MAX_ATTEMPTS = 4


@dataclass
class LLMResult:
    text: str
    stub: bool = False


def _key() -> str | None:
    k = get_settings().gemini_api_key
    return k if k and not k.startswith("AIzaSyxxxx") else None


def _request(path: str, key: str, body: dict) -> dict:
    headers = {"x-goog-api-key": key, "Content-Type": "application/json"}
    last: Exception | None = None
    for attempt in range(_MAX_ATTEMPTS):
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
            time.sleep(1.5 ** attempt)
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

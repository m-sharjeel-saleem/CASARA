"""LLM client with multi-provider, multi-key fallback.

Backends are tried in priority order until one returns a valid JSON response:
  1..N  Gemini keys  (gemini-2.5-flash-lite, "thinking" disabled for speed)
  N+1   Groq         (OpenAI-compatible, separate quota pool — final backstop)

Design goals:
- The AI layer is ADDITIVE. If every backend is exhausted/unavailable, complete_json
  returns None and the review still completes on deterministic scanners.
- A 429 (quota) on one backend immediately advances to the next — no wasted retries.
- Transient errors (5xx / network) retry briefly on the same backend, then advance.
- Per-provider pacing keeps us under free-tier rate limits without slowing fast providers.
"""
import json
import logging
import threading
import time
from dataclasses import dataclass

import httpx

from app.config import get_settings

log = logging.getLogger("casara.llm")

_GEMINI_BASE = "https://generativelanguage.googleapis.com/v1beta"
_GROQ_URL = "https://api.groq.com/openai/v1/chat/completions"
_RETRY_STATUS = {500, 502, 503, 504}   # transient → retry same backend
_ATTEMPTS_PER_BACKEND = 2

# Per-provider minimum spacing (seconds). Gemini free tier is the tight one; Groq is generous.
_PACE = {"gemini": 4.0, "groq": 1.0}
_pace_lock = threading.Lock()
_last_call: dict[str, float] = {}

_degraded = [0]   # failed-call count since last reset (for the "AI rate-limited" notice)


class _QuotaError(Exception):
    """Backend is rate/quota limited (HTTP 429) — move to the next backend."""


class _BackendError(Exception):
    """Backend failed (transient/auth/parse) after local retries — move to the next backend."""


def reset_degraded() -> None:
    _degraded[0] = 0


def degraded_count() -> int:
    return _degraded[0]


@dataclass
class _Backend:
    provider: str   # "gemini" | "groq"
    key: str
    model: str


def _backends() -> list[_Backend]:
    s = get_settings()
    out: list[_Backend] = [_Backend("gemini", k, s.model_fast) for k in s.gemini_keys]
    out += [_Backend("groq", k, s.groq_model) for k in s.groq_keys]
    return out


def available() -> bool:
    return bool(_backends())


def _throttle(provider: str) -> None:
    interval = _PACE.get(provider, 0.0) * (get_settings().gemini_min_interval_s / 4.0
                                           if provider == "gemini" else 1.0)
    if interval <= 0:
        return
    with _pace_lock:
        wait = interval - (time.monotonic() - _last_call.get(provider, 0.0))
        if wait > 0:
            time.sleep(wait)
        _last_call[provider] = time.monotonic()


def _post(url: str, headers: dict, body: dict, provider: str) -> dict:
    """POST with per-provider pacing + transient retries. Raises _QuotaError / _BackendError."""
    last: Exception | None = None
    for attempt in range(_ATTEMPTS_PER_BACKEND):
        _throttle(provider)
        try:
            r = httpx.post(url, headers=headers, json=body, timeout=90)
            if r.status_code == 429:
                raise _QuotaError()
            if r.status_code in _RETRY_STATUS:
                last = _BackendError(f"transient {r.status_code}")
            else:
                r.raise_for_status()
                return r.json()
        except _QuotaError:
            raise
        except (httpx.TransportError, httpx.HTTPStatusError) as e:
            last = _BackendError(str(e))
        if attempt < _ATTEMPTS_PER_BACKEND - 1:
            time.sleep(2.0 * (attempt + 1))
    raise last or _BackendError("unknown")


def _gemini_text(b: _Backend, system: str, prompt: str) -> str:
    body = {
        "contents": [{"parts": [{"text": prompt}]}],
        "systemInstruction": {"parts": [{"text": system}]},
        "generationConfig": {
            "response_mime_type": "application/json",
            "thinkingConfig": {"thinkingBudget": 0},
        },
    }
    data = _post(f"{_GEMINI_BASE}/models/{b.model}:generateContent",
                 {"x-goog-api-key": b.key, "Content-Type": "application/json"}, body, "gemini")
    return data["candidates"][0]["content"]["parts"][0]["text"]


def _groq_text(b: _Backend, system: str, prompt: str) -> str:
    body = {
        "model": b.model,
        "messages": [{"role": "system", "content": system}, {"role": "user", "content": prompt}],
        "response_format": {"type": "json_object"},
        "temperature": 0.2,
    }
    data = _post(_GROQ_URL,
                 {"Authorization": f"Bearer {b.key}", "Content-Type": "application/json"}, body, "groq")
    return data["choices"][0]["message"]["content"]


def complete_json(system: str, prompt: str, *, model: str | None = None) -> object:
    """JSON completion across all backends. Returns parsed JSON, or None if all unavailable."""
    backends = _backends()
    if not backends:
        return None
    if model:  # explicit model override applies to gemini backends only
        backends = [_Backend(b.provider, b.key, model if b.provider == "gemini" else b.model)
                    for b in backends]

    for i, b in enumerate(backends):
        try:
            text = _gemini_text(b, system, prompt) if b.provider == "gemini" \
                else _groq_text(b, system, prompt)
        except _QuotaError:
            log.info("backend %d/%d (%s) quota-limited — trying next", i + 1, len(backends), b.provider)
            continue
        except _BackendError as e:
            log.warning("backend %d/%d (%s) failed: %s — trying next", i + 1, len(backends), b.provider, e)
            continue
        except (KeyError, IndexError, TypeError) as e:
            log.warning("backend %d/%d (%s) malformed response: %s", i + 1, len(backends), b.provider, e)
            continue
        try:
            return json.loads(text)
        except (json.JSONDecodeError, TypeError):
            log.warning("backend %d/%d (%s) returned non-JSON; trying next", i + 1, len(backends), b.provider)
            continue

    _degraded[0] += 1
    log.warning("all %d LLM backend(s) unavailable — degrading to no AI findings", len(backends))
    return None

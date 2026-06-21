"""Agentic auto-fix: turn a finding into a concrete GitHub 'suggested change'.

CASARA's remediation differentiator. For each fixable finding we ask the model for a
minimal replacement of a contiguous line range, then render it as a GitHub suggestion
block so the PR author can apply it with one click.

We only attempt fixes for findings that (a) name a file and line and (b) are at least
medium severity — low-confidence speculation is not worth a code suggestion.
"""
from __future__ import annotations

from dataclasses import dataclass

from app.agents.prompts import FIX_SYSTEM
from app.models import Finding
from app.services import llm

# How many lines of context to show the model on each side of the finding.
_CONTEXT = 8
_FIXABLE_SEVERITIES = {"critical", "high", "medium"}


@dataclass
class Suggestion:
    file: str
    start_line: int      # 1-based, inclusive
    end_line: int        # 1-based, inclusive
    replacement: str
    explanation: str
    finding: Finding


def _window(source: str, line: int) -> tuple[int, int, str]:
    """Return (start, end, numbered_snippet) around a 1-based line."""
    lines = source.splitlines()
    start = max(1, line - _CONTEXT)
    end = min(len(lines), line + _CONTEXT)
    numbered = "\n".join(f"{n}: {lines[n - 1]}" for n in range(start, end + 1))
    return start, end, numbered


def generate(finding: Finding, file_source: str | None) -> Suggestion | None:
    """Produce a one-click Suggestion for a finding, or None if not fixable."""
    if finding.severity not in _FIXABLE_SEVERITIES:
        return None
    if not finding.file or not finding.line or not file_source:
        return None

    win_start, win_end, snippet = _window(file_source, finding.line)
    prompt = (
        f"Finding: [{finding.severity}] {finding.cwe_id} {finding.message}\n"
        f"Fix guidance: {finding.fix_prompt}\n"
        f"File: {finding.file}\n"
        f"Source (line: text), the issue is at line {finding.line}:\n{snippet}"
    )
    raw = llm.complete_json(FIX_SYSTEM, prompt)
    if not isinstance(raw, dict):
        return None

    try:
        start = int(raw.get("start_line", 0))
        end = int(raw.get("end_line", 0))
    except (TypeError, ValueError):
        return None
    replacement = str(raw.get("replacement", ""))

    # Reject empty fixes and ranges outside the window we actually showed the model.
    if not replacement.strip() or start < win_start or end > win_end or end < start:
        return None

    return Suggestion(
        file=finding.file, start_line=start, end_line=end,
        replacement=replacement.rstrip("\n"),
        explanation=str(raw.get("explanation", "")), finding=finding,
    )

"""LLM agents: Security and Logic reviewers, plus an Aggregator/summary step.

Each agent is grounded in scanner output and the diff. Without a Gemini key the
agents return [] (the deterministic scanner findings still flow through), so the
system remains useful keyless.
"""
from app.agents.prompts import (
    AI_CODE_SYSTEM,
    LOGIC_SYSTEM,
    SECURITY_SYSTEM,
    SUMMARY_SYSTEM,
)
from app.core.security import wrap_untrusted
from app.models import Finding
from app.services import llm
from app.services.scanners import cvss_for

_VALID_SEV = {"info", "low", "medium", "high", "critical"}
_VALID_CONF = {"LOW", "MEDIUM", "HIGH"}


def _scanner_context(findings: list[Finding]) -> str:
    if not findings:
        return "(no scanner findings)"
    return "\n".join(
        f"- [{f.source}] {f.severity} {f.cwe_id} {f.file}:{f.line} — {f.message}"
        for f in findings
    )


def _parse(raw: object, source: str) -> list[Finding]:
    if not isinstance(raw, list):
        return []
    out: list[Finding] = []
    for item in raw:
        if not isinstance(item, dict) or not item.get("message"):
            continue
        sev = str(item.get("severity", "medium")).lower()
        sev = sev if sev in _VALID_SEV else "medium"
        conf = str(item.get("confidence", "MEDIUM")).upper()
        out.append(Finding(
            source=source,
            file=str(item.get("file", "")),
            line=item.get("line") if isinstance(item.get("line"), int) else None,
            cwe_id=str(item.get("cwe_id", "")),
            severity=sev, cvss_estimate=cvss_for(sev),
            message=str(item.get("message", "")),
            fix_prompt=str(item.get("fix_prompt", "")),
            confidence=conf if conf in _VALID_CONF else "MEDIUM",
            ai_signal=str(item.get("ai_signal", "")),
        ))
    return out


def _agent(system: str, source: str, diff: str, scanner_findings: list[Finding]) -> list[Finding]:
    prompt = (
        f"Scanner findings (verified signals):\n{_scanner_context(scanner_findings)}\n\n"
        f"Pull-request diff:\n{wrap_untrusted(diff)}"
    )
    return _parse(llm.complete_json(system, prompt), source)


def security_agent(diff: str, scanner_findings: list[Finding]) -> list[Finding]:
    return _agent(SECURITY_SYSTEM, "security-agent", diff, scanner_findings)


def logic_agent(diff: str, scanner_findings: list[Finding]) -> list[Finding]:
    return _agent(LOGIC_SYSTEM, "logic-agent", diff, scanner_findings)


def aicode_agent(
    diff: str, scanner_findings: list[Finding], changed_files: list[str] | None = None
) -> list[Finding]:
    """Detect security problems characteristic of AI-generated code.

    This is CASARA's differentiator. It also sees the list of changed file paths so it
    can flag new/suspicious dependencies and poisoned AI-assistant config files.
    """
    files_note = (
        "Changed files in this PR:\n" + "\n".join(f"- {p}" for p in (changed_files or []))
        if changed_files else "(file list unavailable)"
    )
    prompt = (
        f"Scanner findings (verified signals):\n{_scanner_context(scanner_findings)}\n\n"
        f"{files_note}\n\n"
        f"Pull-request diff:\n{wrap_untrusted(diff)}"
    )
    return _parse(llm.complete_json(AI_CODE_SYSTEM, prompt), "ai-code-agent")


def summarize(findings: list[Finding], risk_score: float, gated: bool) -> str:
    listing = "\n".join(f"- {f.severity} {f.cwe_id} {f.file}: {f.message}" for f in findings)
    raw = llm.complete_json(
        SUMMARY_SYSTEM,
        f"Risk score: {risk_score}/10 (gated={gated}).\nFindings:\n{listing or '(none)'}",
    )
    if isinstance(raw, dict) and raw.get("summary"):
        return str(raw["summary"])
    # Deterministic fallback summary when the LLM is unavailable.
    verb = "blocked from merging" if gated else "allowed to merge"
    return (f"CASARA found {len(findings)} finding(s); composite risk **{risk_score}/10**. "
            f"This PR is **{verb}** under the configured policy.")

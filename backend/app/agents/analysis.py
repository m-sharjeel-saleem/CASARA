"""LLM agents: Security and Logic reviewers, plus an Aggregator/summary step.

Each agent is grounded in scanner output and the diff. Without a Gemini key the
agents return [] (the deterministic scanner findings still flow through), so the
system remains useful keyless.
"""
from app.agents.prompts import (
    AI_CODE_SYSTEM,
    CRITIC_SYSTEM,
    IAC_SYSTEM,
    LOGIC_SYSTEM,
    PRIVACY_SYSTEM,
    SECURITY_SYSTEM,
    SUMMARY_SYSTEM,
    TRIAGE_SYSTEM,
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
    # Gemini (json mime) returns a bare array; Groq (json_object mode) wraps it in an
    # object like {"findings": [...]}. Accept both by unwrapping the first list value.
    if isinstance(raw, dict):
        raw = next((v for v in raw.values() if isinstance(v, list)), [])
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


def _custom_block(custom_instructions: str) -> str:
    if not custom_instructions:
        return ""
    return ("\n\nTeam-specific review rules (from .casara.yml) — prioritise these:\n"
            f"{custom_instructions}")


def _agent(system: str, source: str, diff: str, scanner_findings: list[Finding],
           custom_instructions: str = "") -> list[Finding]:
    prompt = (
        f"Scanner findings (verified signals):\n{_scanner_context(scanner_findings)}"
        f"{_custom_block(custom_instructions)}\n\n"
        f"Pull-request diff:\n{wrap_untrusted(diff)}"
    )
    return _parse(llm.complete_json(system, prompt), source)


def security_agent(diff: str, scanner_findings: list[Finding],
                   custom_instructions: str = "") -> list[Finding]:
    return _agent(SECURITY_SYSTEM, "security-agent", diff, scanner_findings, custom_instructions)


def logic_agent(diff: str, scanner_findings: list[Finding],
                custom_instructions: str = "") -> list[Finding]:
    return _agent(LOGIC_SYSTEM, "logic-agent", diff, scanner_findings, custom_instructions)


def iac_agent(diff: str, scanner_findings: list[Finding], changed_files: list[str] | None = None,
              custom_instructions: str = "") -> list[Finding]:
    """Infrastructure / CI / container security (GitHub Actions supply-chain, Dockerfile, IaC)."""
    files_note = ("Changed files:\n" + "\n".join(f"- {p}" for p in (changed_files or []))
                  if changed_files else "")
    prompt = (f"Scanner findings:\n{_scanner_context(scanner_findings)}{_custom_block(custom_instructions)}\n\n"
              f"{files_note}\n\nPull-request diff:\n{wrap_untrusted(diff)}")
    return _parse(llm.complete_json(IAC_SYSTEM, prompt), "iac-agent")


def privacy_agent(diff: str, scanner_findings: list[Finding],
                  custom_instructions: str = "") -> list[Finding]:
    """Privacy / personal-data handling (PII in logs, plaintext sensitive data, 3rd-party leakage)."""
    return _agent(PRIVACY_SYSTEM, "privacy-agent", diff, scanner_findings, custom_instructions)


# File globs that make the IaC and privacy agents worth running (conditional routing).
_IAC_HINTS = (".github/workflows/", "dockerfile", ".tf", ".tfvars", "/k8s/", "kubernetes",
              "docker-compose", ".yaml", ".yml", "helm", "terraform", ".gitlab-ci")
_PRIVACY_HINTS = ("user", "account", "profile", "auth", "login", "payment", "patient", "customer",
                  "log", "analytics", "track", "export", "email", "person", "pii", "gdpr")


def should_run_iac(files: list[str]) -> bool:
    blob = " ".join(files).lower()
    return any(h in blob for h in _IAC_HINTS)


def should_run_privacy(files: list[str]) -> bool:
    blob = " ".join(files).lower()
    return any(h in blob for h in _PRIVACY_HINTS)


def aicode_agent(
    diff: str, scanner_findings: list[Finding], changed_files: list[str] | None = None,
    custom_instructions: str = "",
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
        f"Scanner findings (verified signals):\n{_scanner_context(scanner_findings)}"
        f"{_custom_block(custom_instructions)}\n\n"
        f"{files_note}\n\n"
        f"Pull-request diff:\n{wrap_untrusted(diff)}"
    )
    return _parse(llm.complete_json(AI_CODE_SYSTEM, prompt), "ai-code-agent")


_SEV_RANK = {"critical": 4, "high": 3, "medium": 2, "low": 1, "info": 0}


def critic(diff: str, findings: list[Finding]) -> list[Finding]:
    """Grounded critic loop: drop/downgrade likely false positives among UNVERIFIED findings.

    Scanner-grounded (verified) findings are never dropped — only AI-only findings are
    subject to the critic, and the critique is grounded in the diff + scanner output (per
    the research: ungrounded reflection adds little). Returns the surviving findings.
    """
    candidates = [(i, f) for i, f in enumerate(findings) if not f.verified]
    if not candidates:
        return findings

    listing = "\n".join(
        f"[{i}] {f.severity} {f.cwe_id} {f.file}:{f.line} ({f.source}) — {f.message}"
        for i, f in candidates
    )
    raw = llm.complete_json(
        CRITIC_SYSTEM,
        f"Candidate findings:\n{listing}\n\nPull-request diff:\n{wrap_untrusted(diff)}",
    )
    if not isinstance(raw, dict):
        return findings  # critic unavailable (keyless) → keep everything

    drop = {int(i) for i in raw.get("drop", []) if isinstance(i, int)}
    downgrade = {int(d["index"]): str(d.get("severity", "")).lower()
                 for d in raw.get("downgrade", []) if isinstance(d, dict) and "index" in d}

    out: list[Finding] = []
    for i, f in enumerate(findings):
        if i in drop and not f.verified:
            continue
        if i in downgrade and downgrade[i] in _VALID_SEV and not f.verified:
            f.severity = downgrade[i]  # type: ignore[assignment]
        out.append(f)
    return out


_EXPLOIT = {"high", "medium", "low", "noise"}


def triage(diff: str, findings: list[Finding]) -> list[Finding]:
    """Rank findings by real-world exploitability in one pass. Sets priority (0-100) and an
    exploitability label; downgrades 'noise' to info severity so it stops inflating the score.
    Sorts by priority. Without an LLM backend, applies a sane deterministic priority."""
    if not findings:
        return findings

    if not llm.available():
        for f in findings:  # deterministic fallback: severity drives priority
            f.priority = {"critical": 95, "high": 80, "medium": 55, "low": 30, "info": 10}.get(f.severity, 40)
            f.exploitability = f.exploitability or ("high" if f.severity in ("critical", "high") else "medium")
        findings.sort(key=lambda f: f.priority, reverse=True)
        return findings

    listing = "\n".join(
        f"[{i}] {f.severity} {f.cwe_id} {f.file}:{f.line} ({f.source}{' verified' if f.verified else ''}) — {f.message}"
        for i, f in enumerate(findings)
    )
    raw = llm.complete_json(TRIAGE_SYSTEM,
                            f"Findings:\n{listing}\n\nContext:\n{wrap_untrusted(diff)}")
    verdicts = raw.get("verdicts", []) if isinstance(raw, dict) else []
    by_idx = {int(v["index"]): v for v in verdicts if isinstance(v, dict) and "index" in v}

    for i, f in enumerate(findings):
        v = by_idx.get(i)
        if not v:
            f.priority = f.priority or 50
            continue
        exp = str(v.get("exploitability", "")).lower()
        f.exploitability = exp if exp in _EXPLOIT else "medium"
        try:
            f.priority = max(0, min(100, int(v.get("priority", 50))))
        except (TypeError, ValueError):
            f.priority = 50
        # Real-world noise stops inflating the risk score / grade, but stays visible.
        if f.exploitability == "noise" and not f.verified:
            f.severity = "info"  # type: ignore[assignment]
            f.cvss_estimate = 1.0
    findings.sort(key=lambda f: f.priority, reverse=True)
    return findings


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

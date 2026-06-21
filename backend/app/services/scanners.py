"""Deterministic scanner integrations: Semgrep, Bandit, Gitleaks.

Each runs as a subprocess and is skipped gracefully if its CLI is not installed,
so the pipeline never hard-fails on a missing tool. Outputs are normalized to
the shared Finding model.
"""
import json
import logging
import shutil
import subprocess

from app.models import Finding, Severity
from app.services import depscan

log = logging.getLogger("casara.scanners")

# Severity → representative CVSS estimate for the risk score.
_CVSS = {"critical": 9.0, "high": 7.5, "medium": 5.0, "low": 3.0, "info": 1.0}


def cvss_for(sev: Severity) -> float:
    return _CVSS.get(sev, 5.0)


def _available(tool: str) -> bool:
    if shutil.which(tool) is None:
        log.info("scanner %s not installed — skipping", tool)
        return False
    return True


def _run(cmd: list[str], cwd: str, timeout: int = 120) -> str | None:
    try:
        proc = subprocess.run(cmd, cwd=cwd, capture_output=True, text=True, timeout=timeout)
        return proc.stdout
    except (subprocess.TimeoutExpired, OSError) as e:
        log.warning("scanner %s failed: %s", cmd[0], e)
        return None


def run_semgrep(path: str) -> list[Finding]:
    if not _available("semgrep"):
        return []
    out = _run(["semgrep", "--config", "auto", "--json", "--quiet", path], path)
    if not out:
        return []
    findings: list[Finding] = []
    for r in json.loads(out).get("results", []):
        extra = r.get("extra", {})
        sev = {"ERROR": "high", "WARNING": "medium", "INFO": "low"}.get(
            extra.get("severity", "WARNING"), "medium"
        )
        cwe = (extra.get("metadata", {}).get("cwe") or [""])
        findings.append(Finding(
            source="semgrep", file=r.get("path", ""),
            line=r.get("start", {}).get("line"),
            cwe_id=(cwe[0] if isinstance(cwe, list) else str(cwe)),
            severity=sev, cvss_estimate=cvss_for(sev),
            message=extra.get("message", ""), confidence="HIGH",
        ))
    return findings


def run_bandit(path: str) -> list[Finding]:
    if not _available("bandit"):
        return []
    out = _run(["bandit", "-r", "-f", "json", "-q", path], path)
    if not out:
        return []
    findings: list[Finding] = []
    for r in json.loads(out).get("results", []):
        sev = {"HIGH": "high", "MEDIUM": "medium", "LOW": "low"}.get(
            r.get("issue_severity", "MEDIUM"), "medium"
        )
        findings.append(Finding(
            source="bandit", file=r.get("filename", ""), line=r.get("line_number"),
            cwe_id=str(r.get("issue_cwe", {}).get("id", "")),
            severity=sev, cvss_estimate=cvss_for(sev),
            message=r.get("issue_text", ""), confidence="HIGH",
        ))
    return findings


def run_gitleaks(path: str) -> list[Finding]:
    if not _available("gitleaks"):
        return []
    out = _run(["gitleaks", "detect", "--no-git", "--report-format", "json",
                "--report-path", "/dev/stdout", "-s", path], path)
    if not out:
        return []
    try:
        leaks = json.loads(out)
    except json.JSONDecodeError:
        return []
    return [Finding(
        source="gitleaks", file=l.get("File", ""), line=l.get("StartLine"),
        cwe_id="CWE-798", severity="critical", cvss_estimate=9.0,
        message=f"Potential secret: {l.get('Description', 'detected credential')}",
        confidence="MEDIUM",
    ) for l in (leaks or [])]


def scan_directory(path: str) -> list[Finding]:
    """Run every available scanner over a checked-out repository path."""
    findings: list[Finding] = []
    for runner in (run_semgrep, run_bandit, run_gitleaks, depscan.scan_dependencies):
        try:
            findings.extend(runner(path))
        except Exception as e:  # noqa: BLE001 — one scanner must not break the run
            log.warning("scanner error in %s: %s", runner.__name__, e)
    return findings

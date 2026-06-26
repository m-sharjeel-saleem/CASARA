"""Deterministic scanner integrations: Semgrep, Bandit, Gitleaks.

Each runs as a subprocess and is skipped gracefully if its CLI is not installed,
so the pipeline never hard-fails on a missing tool. Outputs are normalized to
the shared Finding model.
"""
import json
import logging
import os
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


def run_semgrep(path: str, extra_config: str = "") -> list[Finding]:
    if not _available("semgrep"):
        return []
    cmd = ["semgrep", "--config", "auto"]
    if extra_config:
        # User-supplied registry pack or repo-relative rules (declarative AST rules).
        ref = extra_config if extra_config.startswith("p/") else os.path.join(path, extra_config)
        cmd += ["--config", ref]
    # Bound runtime so a slow registry fetch / huge file can't stall the review.
    cmd += ["--timeout", "20", "--max-target-bytes", "1000000", "--json", "--quiet", path]
    out = _run(cmd, path, timeout=90)
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


def scan_directory(path: str, semgrep_config: str = "") -> list[Finding]:
    """Run every available scanner over a checked-out repository path.

    `semgrep_config` (from .casara.yml) adds a user-supplied declarative ruleset."""
    findings: list[Finding] = []
    runners = [
        lambda p: run_semgrep(p, semgrep_config),
        run_bandit, run_gitleaks, depscan.scan_dependencies,
    ]
    for runner in runners:
        try:
            findings.extend(runner(path))
        except Exception as e:  # noqa: BLE001 — one scanner must not break the run
            name = getattr(runner, "__name__", "semgrep")
            log.warning("scanner error in %s: %s", name, e)
    return findings

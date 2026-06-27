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


def run_osv(path: str) -> list[Finding]:
    """OSV-Scanner — dependency vulnerabilities from 20+ advisory sources (CVE/GHSA)."""
    if not _available("osv-scanner"):
        return []
    # `scan source` is the current verb; fall back to legacy flags on older binaries.
    out = _run(["osv-scanner", "scan", "source", "--recursive", "--format", "json", path],
               path, timeout=180) or _run(["osv-scanner", "--format", "json", "-r", path], path, 180)
    if not out:
        return []
    findings: list[Finding] = []
    try:
        data = json.loads(out)
    except json.JSONDecodeError:
        return []
    for res in data.get("results", []):
        rel = res.get("source", {}).get("path", "")
        for pkg in res.get("packages", []):
            name = pkg.get("package", {}).get("name", "dependency")
            for v in pkg.get("vulnerabilities", []):
                vid = v.get("id", "")
                sev = _osv_severity(v, pkg)
                findings.append(Finding(
                    source="osv-scanner", file=rel, cwe_id=vid, severity=sev,
                    cvss_estimate=cvss_for(sev), confidence="HIGH",
                    message=f"{name}: {v.get('summary') or vid}",
                    fix_prompt="Upgrade to a non-vulnerable version of this dependency.",
                ))
    return findings


def _osv_severity(v: dict, pkg: dict) -> Severity:
    grp = pkg.get("groups", [{}])
    mx = (grp[0].get("max_severity") if grp else None) or ""
    try:
        score = float(mx)
        return ("critical" if score >= 9 else "high" if score >= 7
                else "medium" if score >= 4 else "low")
    except (TypeError, ValueError):
        return "high"  # a known CVE with unknown score is at least high by default


def run_guarddog(path: str) -> list[Finding]:
    """GuardDog (DataDog) — malicious/compromised PyPI & npm packages (the malware scanner)."""
    if not _available("guarddog"):
        return []
    findings: list[Finding] = []
    targets = [("pypi", "requirements.txt"), ("npm", "package.json")]
    for ecosystem, manifest in targets:
        full = os.path.join(path, manifest)
        if not os.path.exists(full):
            continue
        out = _run(["guarddog", ecosystem, "verify", full, "--output-format", "json"], path, 180)
        if not out:
            continue
        try:
            data = json.loads(out)
        except json.JSONDecodeError:
            continue
        for entry in (data if isinstance(data, list) else [data]):
            for issue in entry.get("issues", []) if isinstance(entry, dict) else []:
                findings.append(Finding(
                    source="guarddog", file=manifest, cwe_id="CWE-506", severity="critical",
                    cvss_estimate=9.5, confidence="HIGH", verified=True,
                    message=f"Malicious-package signal in {entry.get('package', ecosystem)}: {issue}",
                    fix_prompt="Remove this dependency and audit any machine that installed it.",
                ))
    return findings


def run_trivy(path: str) -> list[Finding]:
    """Trivy — misconfiguration (IaC) + secrets. Vuln DB skipped to stay fast on free infra."""
    if not _available("trivy"):
        return []
    out = _run(["trivy", "fs", "--scanners", "misconfig,secret", "--format", "json",
                "--quiet", path], path, 240)
    if not out:
        return []
    findings: list[Finding] = []
    try:
        data = json.loads(out)
    except json.JSONDecodeError:
        return []
    _tsev = {"CRITICAL": "critical", "HIGH": "high", "MEDIUM": "medium", "LOW": "low", "UNKNOWN": "low"}
    for res in data.get("Results", []):
        tgt = res.get("Target", "")
        for m in res.get("Misconfigurations", []):
            sev = _tsev.get(m.get("Severity", "MEDIUM"), "medium")
            findings.append(Finding(
                source="trivy", file=tgt, cwe_id=m.get("ID", ""), severity=sev,
                cvss_estimate=cvss_for(sev), confidence="HIGH",
                message=f"{m.get('Title', 'Misconfiguration')}: {m.get('Description', '')}"[:300],
                fix_prompt=m.get("Resolution", "") or "Apply the recommended secure configuration.",
            ))
        for s in res.get("Secrets", []):
            findings.append(Finding(
                source="trivy", file=tgt, line=s.get("StartLine"), cwe_id="CWE-798",
                severity="critical", cvss_estimate=9.0, confidence="MEDIUM",
                message=f"Potential secret: {s.get('Title', s.get('RuleID', 'credential'))}",
                fix_prompt="Remove the secret and rotate the credential.",
            ))
    return findings


def scan_directory(path: str, semgrep_config: str = "") -> list[Finding]:
    """Fast PR-diff scan: lightweight scanners over the changed-files checkout."""
    return _run_all(path, [
        lambda p: run_semgrep(p, semgrep_config),
        run_bandit, run_gitleaks, depscan.scan_dependencies,
    ])


def scan_full(path: str, semgrep_config: str = "") -> list[Finding]:
    """Whole-repo audit scan: the full powerful suite (heavier, runs over the entire repo)."""
    return _run_all(path, [
        lambda p: run_semgrep(p, semgrep_config),
        run_bandit, run_gitleaks, depscan.scan_dependencies,
        run_osv, run_guarddog, run_trivy,
    ])


def _run_all(path: str, runners: list) -> list[Finding]:
    findings: list[Finding] = []
    for runner in runners:
        try:
            found = runner(path)
            findings.extend(found)
            log.info("scanner %s: %d findings", getattr(runner, "__name__", "semgrep"), len(found))
        except Exception as e:  # noqa: BLE001 — one scanner must not break the run
            log.warning("scanner error in %s: %s", getattr(runner, "__name__", "semgrep"), e)
    return findings

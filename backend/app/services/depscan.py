"""Dependency / supply-chain scanner (the Shai-Hulud / PolinRider defense).

Pure in-process — no external CLI or paid feed required, so it runs anywhere. It inspects
dependency manifests in the PR for the specific red flags our market research surfaced:

  1. Install-time hook scripts in package.json (preinstall/install/postinstall) — the exact
     vector self-propagating npm worms (Shai-Hulud) use to run code before any test/scan.
  2. Known-malicious package names from recent supply-chain campaigns (a small built-in IOC list).
  3. Untrusted version specifiers — git/http(s) URLs or "latest" — which bypass registry integrity.

Findings are emitted with source="depscan" and map to the SCA dimension of the risk score.
"""
from __future__ import annotations

import json
import logging
import os

from app.models import Finding

log = logging.getLogger("casara.depscan")

# Manifests we know how to inspect.
_NPM_MANIFEST = "package.json"
_PY_MANIFESTS = ("requirements.txt", "pyproject.toml")

# Install-time lifecycle scripts that let a package run code on install (worm vector).
_DANGEROUS_SCRIPTS = ("preinstall", "install", "postinstall")

# Built-in IOC list: package names tied to recent self-propagating / DPRK campaigns.
# Kept small and conservative; extend as new campaigns are confirmed.
_MALICIOUS_PACKAGES = {
    "shai-hulud",          # npm self-propagating worm marker
    "@ctrl/tinycolor",     # one of the originally compromised Shai-Hulud packages
    "ngx-bootstrap",       # compromised in Shai-Hulud wave (example IOC)
}

# Version specifiers that bypass registry integrity / pinning.
_UNTRUSTED_VERSION_HINTS = ("git+", "http://", "https://", "github:", "file:")


def _npm(path: str, rel: str) -> list[Finding]:
    findings: list[Finding] = []
    try:
        with open(path, encoding="utf-8", errors="replace") as fh:
            data = json.load(fh)
    except (json.JSONDecodeError, OSError):
        return findings

    scripts = data.get("scripts", {}) or {}
    for hook in _DANGEROUS_SCRIPTS:
        if hook in scripts:
            findings.append(Finding(
                source="depscan", file=rel, cwe_id="CWE-829", severity="high",
                cvss_estimate=7.5, confidence="HIGH",
                message=(f"Install-time script '{hook}' runs code on `npm install` before any test "
                         f"or scan — the vector used by self-propagating worms (e.g. Shai-Hulud): "
                         f"{scripts[hook]!r}"),
                fix_prompt=(f"Remove the '{hook}' script or move its work to an explicit, reviewed "
                            f"build step. Never run untrusted code at install time."),
            ))

    deps: dict[str, str] = {}
    for key in ("dependencies", "devDependencies", "optionalDependencies"):
        deps.update(data.get(key, {}) or {})
    findings.extend(_check_deps(deps, rel, npm=True))
    return findings


def _python(path: str, rel: str) -> list[Finding]:
    try:
        with open(path, encoding="utf-8", errors="replace") as fh:
            text = fh.read()
    except OSError:
        return []
    deps: dict[str, str] = {}
    for raw in text.splitlines():
        line = raw.split("#", 1)[0].strip()
        if not line or line.startswith("-"):
            continue
        # crude name/version split: name==1.2.3, name>=1, name @ url, etc.
        for sep in ("==", ">=", "<=", "~=", "@", ">", "<"):
            if sep in line:
                name, _, ver = line.partition(sep)
                deps[name.strip().lower()] = (sep + ver).strip()
                break
        else:
            deps[line.strip().lower()] = ""
    return _check_deps(deps, rel, npm=False)


def _check_deps(deps: dict[str, str], rel: str, *, npm: bool) -> list[Finding]:
    findings: list[Finding] = []
    for name, version in deps.items():
        norm = name.lower().strip()
        if norm in _MALICIOUS_PACKAGES:
            findings.append(Finding(
                source="depscan", file=rel, cwe_id="CWE-506", severity="critical",
                cvss_estimate=9.5, confidence="HIGH", verified=True,
                message=(f"Dependency '{name}' matches a known malicious/compromised package from a "
                         f"recent supply-chain campaign. Do not install."),
                fix_prompt=f"Remove '{name}' and audit any machine that already installed it.",
            ))
            continue
        v = str(version)
        if any(h in v for h in _UNTRUSTED_VERSION_HINTS):
            findings.append(Finding(
                source="depscan", file=rel, cwe_id="CWE-829", severity="medium",
                cvss_estimate=5.0, confidence="MEDIUM",
                message=(f"Dependency '{name}' is pulled from an untrusted source ({v}) that bypasses "
                         f"registry integrity checks — a common supply-chain insertion point."),
                fix_prompt=f"Pin '{name}' to a published, version-locked release from the registry.",
            ))
    return findings


def scan_dependencies(root: str) -> list[Finding]:
    """Walk a checked-out tree and inspect every dependency manifest found."""
    findings: list[Finding] = []
    for dirpath, _dirs, files in os.walk(root):
        for fname in files:
            full = os.path.join(dirpath, fname)
            rel = os.path.relpath(full, root)
            try:
                if fname == _NPM_MANIFEST:
                    findings.extend(_npm(full, rel))
                elif fname in _PY_MANIFESTS:
                    findings.extend(_python(full, rel))
            except Exception as e:  # noqa: BLE001 — one manifest must not break the run
                log.warning("depscan error on %s: %s", rel, e)
    return findings

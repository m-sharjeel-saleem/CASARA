"""Whole-repo security audit — distinct from the fast PR-diff review.

Downloads the entire repository, runs the full powerful scanner suite (Semgrep, Bandit,
Gitleaks, depscan, OSV-Scanner, GuardDog, Trivy), aggregates + dedups, computes a security
grade (A–F), and produces AI remediation recommendations grounded in the findings.

Stored as a Review with pr_number=0 (the "audit" marker) so it reuses all existing storage,
listing, and detail UI with no schema change. Grade is derived from the risk score.
"""
import io
import logging
import os
import tarfile
import tempfile
import uuid
from datetime import datetime, timezone

from app.agents import analysis
from app.core.config_file import load_config
from app.core import events
from app.core.risk import compute_risk, should_gate
from app.db import store
from app.models import Finding, Review
from app.services import github, llm, scanners
from app.services.review import aggregate

log = logging.getLogger("casara.audit")
AUDIT_PR_NUMBER = 0  # marks a Review as a whole-repo audit

# Source extensions the AI reviewer understands; everything else is left to scanners.
_CODE_EXT = {".py", ".js", ".jsx", ".ts", ".tsx", ".go", ".rb", ".php", ".java", ".rs",
             ".c", ".h", ".cpp", ".cs", ".swift", ".kt", ".scala", ".sh", ".sql"}
# Path fragments that signal security-sensitive code — scanned first.
_SENSITIVE = ("auth", "login", "session", "password", "token", "crypto", "secret", "key",
              "payment", "billing", "network", "api", "db", "database", "keychain", "admin")
_SKIP_DIRS = ("/node_modules/", "/.git/", "/vendor/", "/dist/", "/build/", "/.next/",
              "/pods/", "/pod/", "/third_party/", "/.venv/")
_BUNDLE_CAP = 40000   # max chars of source sent to the AI per audit (cost + context bound)


def _code_bundle(root: str) -> tuple[str, list[str]]:
    """Concatenate security-relevant source files (sensitive paths first) up to a cap,
    so the AI agents can review a whole repo in one bounded pass."""
    candidates: list[tuple[int, str]] = []
    for dirpath, _dirs, files in os.walk(root):
        low = (dirpath + "/").lower()
        if any(s in low for s in _SKIP_DIRS):
            continue
        for fn in files:
            if os.path.splitext(fn)[1].lower() not in _CODE_EXT:
                continue
            full = os.path.join(dirpath, fn)
            rel = os.path.relpath(full, root)
            score = 1 if any(s in rel.lower() for s in _SENSITIVE) else 0
            candidates.append((score, full))
    candidates.sort(key=lambda c: c[0], reverse=True)  # sensitive files first

    parts: list[str] = []
    used_files: list[str] = []
    total = 0
    for _score, full in candidates:
        try:
            with open(full, encoding="utf-8", errors="replace") as fh:
                content = fh.read(8000)  # cap per file
        except OSError:
            continue
        rel = os.path.relpath(full, root)
        block = f"\n### FILE: {rel}\n{content}\n"
        if total + len(block) > _BUNDLE_CAP:
            break
        parts.append(block); used_files.append(rel); total += len(block)
    return "".join(parts), used_files


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def grade_for(score: float) -> str:
    """Security grade from composite risk (lower risk = better grade)."""
    return "A" if score < 2 else "B" if score < 4 else "C" if score < 6 else "D" if score < 8 else "F"


def _extract(tarball: bytes, root: str) -> bool:
    try:
        with tarfile.open(fileobj=io.BytesIO(tarball), mode="r:gz") as tf:
            safe = [m for m in tf.getmembers() if not (m.name.startswith("/") or ".." in m.name)]
            tf.extractall(root, members=safe)  # noqa: S202 — members sanitised above
        return True
    except (tarfile.TarError, OSError) as e:
        log.warning("tarball extract failed: %s", e)
        return False


def _recommendations(findings: list[Finding], grade: str, repo: str) -> str:
    """LLM remediation plan grounded ONLY in finding metadata (CodeReduce: no raw code →
    less hallucination). Falls back to a deterministic summary when no LLM backend."""
    top = sorted(findings, key=lambda f: {"critical": 4, "high": 3, "medium": 2, "low": 1, "info": 0}
                 .get(f.severity, 0), reverse=True)[:15]
    listing = "\n".join(f"- [{f.severity}] {f.cwe_id} {f.file} ({f.source}): {f.message}" for f in top)
    system = (
        "You are a senior application-security engineer writing a prioritized remediation plan for a "
        "whole-repository audit. Ground every recommendation in the provided findings — do not invent "
        "issues. Return ONLY JSON: {\"summary\": \"<markdown remediation plan: the security grade "
        "meaning, the top 3-5 prioritized actions, and quick wins>\"}."
    )
    raw = llm.complete_json(system, f"Repository: {repo}\nGrade: {grade}\nFindings:\n{listing or '(none)'}")
    if isinstance(raw, dict) and raw.get("summary"):
        return str(raw["summary"])
    n = len(findings)
    crit = sum(1 for f in findings if f.severity == "critical")
    return (f"Security grade **{grade}** — {n} finding(s), {crit} critical. "
            f"Prioritise the critical and high-severity items above, starting with leaked secrets and "
            f"malicious/vulnerable dependencies, then misconfigurations.")


def run_audit(repo: str, installation_id: int | None = None) -> Review:
    review = Review(
        id=uuid.uuid4().hex[:12], repo=repo, pr_number=AUDIT_PR_NUMBER,
        pr_title=f"Security audit · {repo}", author="audit", installation_id=installation_id,
        status="running", created_at=_now(),
    )
    if installation_id:
        try:
            store.upsert_installation(installation_id, repo.split("/")[0], "", 0, _now())
        except Exception as e:  # noqa: BLE001
            log.warning("ensure installation failed: %s", e)
    store.save_review(review)
    events.publish("review.started", review.model_dump())

    try:
        info = github.get_repo(repo, installation_id)
        ref = info.get("default_branch", "HEAD")
        review.head_sha = ref
        cfg = load_config(repo, ref, installation_id)

        findings: list[Finding] = []
        tarball = github.download_tarball(repo, ref, installation_id)
        if tarball:
            with tempfile.TemporaryDirectory() as root:
                if _extract(tarball, root):
                    # tarball extracts to a single top-level dir
                    entries = [os.path.join(root, d) for d in os.listdir(root)]
                    scan_root = entries[0] if len(entries) == 1 and os.path.isdir(entries[0]) else root
                    log.info("audit %s: scanning %s", review.id, repo)
                    findings = scanners.scan_full(scan_root, cfg.semgrep_config)
                    # AI pass over the repo's source — essential for languages the
                    # deterministic scanners don't cover (e.g. Swift, Kotlin).
                    bundle, used = _code_bundle(scan_root)
                    if bundle:
                        instructions = cfg.instructions_for(used)
                        ai = (analysis.security_agent(bundle, findings, instructions)
                              + analysis.aicode_agent(bundle, findings, used, instructions))
                        log.info("audit %s: AI pass over %d files -> %d findings",
                                 review.id, len(used), len(ai))
                        findings += ai
        else:
            raise RuntimeError("could not download repository tarball")

        review.findings = aggregate(findings)
        review.risk_score, _ = compute_risk(review.findings, [f.file for f in review.findings])
        review.gated, _ = should_gate(review.findings, review.risk_score, cfg.gate.threshold)
        grade = grade_for(review.risk_score)
        review.summary = f"**Security grade: {grade}**\n\n" + _recommendations(review.findings, grade, repo)
        review.status = "completed"
        review.completed_at = _now()
        log.info("audit %s: done, grade %s, %d findings", review.id, grade, len(review.findings))
    except Exception as e:  # noqa: BLE001
        log.exception("audit failed: %s", e)
        review.status = "failed"
        review.summary = f"Audit failed: {e}"
        review.completed_at = _now()

    store.save_review(review)
    events.publish("review.completed", review.model_dump())
    return review

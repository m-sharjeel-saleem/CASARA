"""Review orchestrator — the full pipeline for one pull request.

Runs synchronously inside a FastAPI BackgroundTask (no Celery). Steps:
  materialize files → scan → LLM agents → aggregate → risk score → post → persist.
Each external step degrades gracefully so a partial environment still produces
a useful review.
"""
import logging
import os
import tempfile
import uuid
from datetime import datetime, timezone

from app.agents import analysis, autofix
from app.core import events
from app.core.risk import compute_risk, should_gate
from app.db import store
from app.models import Finding, Review
from app.services import github, scanners

log = logging.getLogger("casara.review")

_SEV_ORDER = {"critical": 4, "high": 3, "medium": 2, "low": 1, "info": 0}


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _materialize(repo: str, files: list[str], ref: str, root: str) -> None:
    """Write the PR's changed files into a temp dir so scanners can run on them."""
    for path in files:
        content = github.fetch_file(repo, path, ref)
        if content is None:
            continue
        dest = os.path.join(root, path)
        os.makedirs(os.path.dirname(dest) or root, exist_ok=True)
        with open(dest, "w", encoding="utf-8", errors="replace") as fh:
            fh.write(content)


def aggregate(findings: list[Finding]) -> list[Finding]:
    """Deduplicate by (cwe, file, line) and flag cross-validated findings.

    A finding confirmed by both a deterministic scanner and an LLM agent is
    marked verified with HIGH confidence — the core hybrid-grounding signal.
    """
    groups: dict[tuple, list[Finding]] = {}
    for f in findings:
        groups.setdefault((f.cwe_id, f.file, f.line), []).append(f)

    merged: list[Finding] = []
    for items in groups.values():
        sources = {i.source for i in items}
        best = max(items, key=lambda i: (_SEV_ORDER.get(i.severity, 0), len(i.fix_prompt)))
        cross = any(s in {"semgrep", "bandit", "gitleaks"} for s in sources) and \
                any(s.endswith("-agent") for s in sources)
        best.verified = cross or best.verified
        if cross:
            best.confidence = "HIGH"
        merged.append(best)
    merged.sort(key=lambda f: _SEV_ORDER.get(f.severity, 0), reverse=True)
    return merged


def _comment(review: Review, breakdown: dict, gate_reason: str) -> str:
    gate = (f"🔴 **PR blocked** — {gate_reason}" if review.gated
            else f"🟢 **Passed** — {gate_reason}")
    head = (f"## 🧭 CASARA Security Review\n\n"
            f"**Composite risk score: {review.risk_score}/10** · {gate}\n\n"
            f"{review.summary}\n\n")
    if not review.findings:
        return head + "_No findings._"
    rows = "\n".join(
        f"| {f.severity.upper()} | `{f.file}:{f.line or '-'}` | {f.cwe_id or '-'} | "
        f"{'✅' if f.verified else ''} | {('🤖 ' + f.ai_signal) if f.ai_signal else ''} | {f.message} |"
        for f in review.findings[:30]
    )
    table = ("| Severity | Location | CWE | Verified | AI signal | Finding |\n"
             "|---|---|---|---|---|---|\n" + rows)
    comp = (f"\n\n<sub>Components — SAST {breakdown['S_sast']} · SCA {breakdown['S_sca']} · "
            f"Secrets {breakdown['S_secrets']} · Context {breakdown['S_context']}</sub>")
    return head + table + comp


def _post_fixes(review: Review, max_fixes: int) -> int:
    """Generate and post one-click suggested fixes for the top fixable findings.

    Capped at `max_fixes` per PR to bound LLM cost. Returns the number posted.
    File content is re-fetched at the PR head so suggestion line numbers line up.
    """
    if max_fixes <= 0:
        return 0
    posted = 0
    file_cache: dict[str, str | None] = {}
    for f in review.findings:
        if posted >= max_fixes:
            break
        if not f.file or not f.line:
            continue
        if f.file not in file_cache:
            file_cache[f.file] = github.fetch_file(review.repo, f.file, review.head_sha)
        sug = autofix.generate(f, file_cache[f.file])
        if sug is None:
            continue
        body = (f"🔧 **CASARA suggested fix** — {f.cwe_id or f.severity}: "
                f"{sug.explanation or f.message}")
        if github.post_suggestion(
            review.repo, review.pr_number, review.head_sha, sug.file,
            sug.start_line, sug.end_line, sug.replacement, body,
        ):
            posted += 1
    return posted


def run_review(repo: str, pr_number: int, pr_title: str, author: str, head_sha: str) -> Review:
    from app.config import get_settings

    review = Review(
        id=uuid.uuid4().hex[:12], repo=repo, pr_number=pr_number, pr_title=pr_title,
        author=author, head_sha=head_sha, status="running", created_at=_now(),
    )
    store.save_review(review)
    events.publish("review.started", review.model_dump())

    try:
        files = github.changed_files(repo, pr_number)
        diff = github.get_diff(repo, pr_number)

        scanner_findings: list[Finding] = []
        with tempfile.TemporaryDirectory() as root:
            _materialize(repo, files, head_sha, root)
            scanner_findings = scanners.scan_directory(root)

        agent_findings = (
            analysis.security_agent(diff, scanner_findings)
            + analysis.logic_agent(diff, scanner_findings)
            + analysis.aicode_agent(diff, scanner_findings, files)
        )

        review.findings = aggregate(scanner_findings + agent_findings)
        review.risk_score, breakdown = compute_risk(review.findings, files)
        review.gated, gate_reason = should_gate(
            review.findings, review.risk_score, get_settings().risk_gate_threshold
        )
        review.summary = analysis.summarize(review.findings, review.risk_score, review.gated)
        review.status = "completed"
        review.completed_at = _now()

        github.post_comment(repo, pr_number, _comment(review, breakdown, gate_reason))
        _post_fixes(review, get_settings().max_autofixes)
        github.set_status(
            repo, head_sha, gated=review.gated,
            description=(f"blocked — {gate_reason}" if review.gated
                         else f"passed — risk {review.risk_score}/10"),
        )
    except Exception as e:  # noqa: BLE001 — record failure rather than crash the worker
        log.exception("review failed: %s", e)
        review.status = "failed"
        review.summary = f"Review failed: {e}"
        review.completed_at = _now()

    store.save_review(review)
    events.publish("review.completed", review.model_dump())
    return review

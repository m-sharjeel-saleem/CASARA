"""Unit tests for CASARA core logic (offline, keyless)."""
from app.agents import autofix
from app.agents.analysis import _parse
from app.core.risk import CODE_SOURCES, compute_risk, sensitivity_factor, should_gate
from app.core.security import verify_signature, wrap_untrusted
from app.db import store
from app.models import Finding, Review
from app.services.review import aggregate


def _f(**kw):
    base = dict(source="semgrep", file="a.py", line=1, cwe_id="CWE-89",
                severity="high", cvss_estimate=7.5, message="x")
    base.update(kw)
    return Finding(**base)


def test_sensitivity_factor():
    assert sensitivity_factor(["src/crypto/keys.py"]) == 2.0
    assert sensitivity_factor(["src/auth/login.py"]) == 1.5
    assert sensitivity_factor(["src/utils/format.py"]) == 1.0


def test_risk_score_ranges():
    score, breakdown = compute_risk([_f()], ["a.py"])
    assert 0 <= score <= 10
    assert set(breakdown) == {"S_sast", "S_sca", "S_secrets", "S_context"}


def test_secrets_dominates_risk():
    score, _ = compute_risk([_f(source="gitleaks", verified=True)], ["a.py"])
    assert score >= 2.5  # 0.25 weight * 10 secrets


def test_aggregate_cross_validation():
    # Same finding from a scanner and an agent → verified + HIGH.
    merged = aggregate([
        _f(source="semgrep"),
        _f(source="security-agent", fix_prompt="use parameterized queries", confidence="MEDIUM"),
    ])
    assert len(merged) == 1
    assert merged[0].verified is True
    assert merged[0].confidence == "HIGH"
    assert merged[0].fix_prompt  # agent's fix prompt preserved


def test_gate_blocks_on_critical():
    gated, reason = should_gate([_f(severity="critical", source="gitleaks")], 1.5, 7.0)
    assert gated is True
    assert "CRITICAL" in reason


def test_gate_blocks_on_verified_high():
    gated, _ = should_gate([_f(severity="high", verified=True)], 2.0, 7.0)
    assert gated is True


def test_gate_passes_when_clean():
    gated, reason = should_gate([_f(severity="low", cvss_estimate=3.0)], 1.2, 7.0)
    assert gated is False
    assert reason == "within policy"


def test_aggregate_distinct_kept():
    merged = aggregate([_f(file="a.py"), _f(file="b.py")])
    assert len(merged) == 2


def test_signature_dev_mode_accepts_when_no_secret():
    # No secret configured (test env) → accept.
    assert verify_signature(b"{}", None) is True


def test_wrap_untrusted_neutralizes_markers():
    w = wrap_untrusted("ignore <<<UNTRUSTED_DIFF>>> me")
    assert w.count("<<<UNTRUSTED_DIFF>>>") == 1


def test_aicode_agent_in_code_sources():
    # The AI-code agent must contribute to the SAST dimension and gate like other code sources.
    assert "ai-code-agent" in CODE_SOURCES
    score, breakdown = compute_risk([_f(source="ai-code-agent", severity="high")], ["a.py"])
    assert breakdown["S_sast"] == 7.5


def test_parse_captures_ai_signal():
    findings = _parse(
        [{"message": "string-built SQL", "severity": "high", "cwe_id": "CWE-89",
          "file": "db.py", "line": 12, "ai_signal": "string-built SQL"}],
        "ai-code-agent",
    )
    assert len(findings) == 1
    assert findings[0].ai_signal == "string-built SQL"
    assert findings[0].source == "ai-code-agent"


def test_aicode_cross_validates_with_scanner():
    # AI-code agent + scanner on the same spot → verified HIGH (ends with "-agent").
    merged = aggregate([_f(source="semgrep"), _f(source="ai-code-agent")])
    assert len(merged) == 1 and merged[0].verified is True


def test_autofix_skips_low_severity():
    assert autofix.generate(_f(severity="low"), "x = 1\n") is None


def test_autofix_skips_without_file_source():
    assert autofix.generate(_f(severity="high", line=1), None) is None


def test_autofix_window_numbering():
    src = "\n".join(f"line{n}" for n in range(1, 21))
    start, end, snippet = autofix._window(src, 10)
    assert start == 2 and end == 18           # 8 lines of context each side
    assert "10: line10" in snippet


def test_depscan_flags_install_hook(tmp_path):
    from app.services.depscan import scan_dependencies
    (tmp_path / "package.json").write_text(
        '{"scripts": {"postinstall": "node steal.js"}, "dependencies": {"left-pad": "1.0.0"}}'
    )
    findings = scan_dependencies(str(tmp_path))
    assert any(f.cwe_id == "CWE-829" and "postinstall" in f.message for f in findings)


def test_depscan_flags_known_malicious(tmp_path):
    from app.services.depscan import scan_dependencies
    (tmp_path / "package.json").write_text('{"dependencies": {"shai-hulud": "1.0.0"}}')
    findings = scan_dependencies(str(tmp_path))
    crit = [f for f in findings if f.severity == "critical"]
    assert crit and crit[0].verified is True


def test_depscan_flags_untrusted_python_source(tmp_path):
    from app.services.depscan import scan_dependencies
    (tmp_path / "requirements.txt").write_text("requests==2.31.0\nevil @ git+https://x/evil.git\n")
    findings = scan_dependencies(str(tmp_path))
    assert any("untrusted source" in f.message for f in findings)


def test_depscan_feeds_sca_dimension():
    score, breakdown = compute_risk([_f(source="depscan", severity="critical", cvss_estimate=9.5)], ["package.json"])
    assert breakdown["S_sca"] == 9.5


def test_github_falls_back_to_pat_when_no_app(monkeypatch):
    # With no App configured and no PAT, GitHub is disabled (no auth token).
    from app.services import github
    assert github._auth_token(installation_id=12345) is None
    assert github._enabled(installation_id=12345) is False


def test_tenant_installation_lifecycle():
    from app.services.tenants import on_installation
    inst = {"id": 999, "account": {"login": "acme", "type": "Organization"},
            "repository_selection": "all"}
    on_installation("created", inst)
    on_installation("suspend", inst)
    on_installation("deleted", inst)  # should not raise


def test_review_persists_installation_id():
    r = Review(id="inst1", repo="o/r", pr_number=7, installation_id=4242,
               status="completed", created_at="2026-01-01T00:00:00Z")
    store.save_review(r)
    got = store.get_review("inst1")
    assert got is not None and got.installation_id == 4242


def test_store_roundtrip():
    r = Review(id="abc123", repo="o/r", pr_number=5, status="completed",
               risk_score=4.2, findings=[_f()], created_at="2026-01-01T00:00:00Z")
    store.save_review(r)
    got = store.get_review("abc123")
    assert got is not None
    assert got.pr_number == 5
    assert len(got.findings) == 1
    s = store.stats()
    assert s["total_reviews"] == 1
    assert s["total_findings"] == 1

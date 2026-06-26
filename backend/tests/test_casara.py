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


def test_parse_unwraps_groq_object():
    # Groq json_object mode wraps the array in an object — parser must unwrap it.
    findings = _parse(
        {"findings": [{"message": "x", "severity": "high", "cwe_id": "CWE-89"}]}, "security-agent")
    assert len(findings) == 1 and findings[0].cwe_id == "CWE-89"
    assert _parse({}, "security-agent") == []  # empty object → no findings


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


def test_metering_counts_and_caps(monkeypatch):
    from app.config import get_settings
    from app.services import metering
    period = metering.current_period()
    assert metering.record_review(555) == 1
    assert metering.record_review(555) == 2
    assert store.get_usage(555, period) == 2
    # No cap configured → never over limit.
    assert metering.over_free_limit(555) is False
    # Set a cap of 2 and confirm it trips.
    get_settings.cache_clear()
    monkeypatch.setenv("FREE_MONTHLY_REVIEWS", "2")
    assert metering.over_free_limit(555) is True
    get_settings.cache_clear()


def test_review_persists_installation_id():
    r = Review(id="inst1", repo="o/r", pr_number=7, installation_id=4242,
               status="completed", created_at="2026-01-01T00:00:00Z")
    store.save_review(r)
    got = store.get_review("inst1")
    assert got is not None and got.installation_id == 4242


def test_config_parses_and_defaults():
    from app.core.config_file import parse_config
    cfg = parse_config("""
version: 1
languages: [python]
gate:
  level: warning
  threshold: 6.0
noise:
  max_comments: 5
  min_confidence: HIGH
rules:
  - path: "src/auth/**"
    instructions: "Be strict about authz."
severity_overrides:
  CWE-89: critical
""")
    assert cfg.languages == ["python"]
    assert cfg.gate.level == "warning" and cfg.gate.threshold == 6.0
    assert cfg.noise.max_comments == 5 and cfg.noise.min_confidence == "HIGH"
    assert cfg.severity_overrides["CWE-89"] == "critical"
    # malformed YAML / wrong types fall back to defaults, never raise
    assert parse_config("::: not yaml :::").gate.level == "error"
    assert parse_config(None).languages == []


def test_config_merge_dashboard_under_repo():
    from app.core.config_file import _build, _merge
    dashboard = {"gate": {"level": "warning"}, "rules": [{"path": "**/*.py", "instructions": "dash"}],
                 "severity_overrides": {"CWE-1": "low"}}
    repo = {"gate": {"level": "error"}, "rules": [{"path": "src/**", "instructions": "repo"}],
            "severity_overrides": {"CWE-89": "critical"}}
    merged = _merge(dashboard, repo)
    cfg = _build(merged)
    assert cfg.gate.level == "error"               # repo overrides dashboard
    assert len(cfg.rules) == 2                      # rules combined
    assert cfg.severity_overrides == {"CWE-1": "low", "CWE-89": "critical"}  # merged


def test_config_persist_roundtrip():
    store.set_config(7777, {"languages": ["python"], "gate": {"level": "warning"}},
                     "2026-06-27T00:00:00Z")
    got = store.get_config(7777)
    assert got["languages"] == ["python"] and got["gate"]["level"] == "warning"


def test_config_instructions_match_glob():
    from app.core.config_file import parse_config
    cfg = parse_config('rules:\n  - path: "**/*.py"\n    instructions: "No eval."')
    assert "No eval" in cfg.instructions_for(["app/main.py"])
    assert cfg.instructions_for(["app/main.js"]) == ""


def test_language_scoping():
    from app.services.review import _scope_by_language
    files = ["a.py", "b.js", "package.json", "c.go"]
    # python only → keep .py + unknown-extension files (configs), drop .js/.go
    assert _scope_by_language(files, ["python"]) == ["a.py", "package.json"]
    # empty → keep all
    assert _scope_by_language(files, []) == files


def test_severity_overrides_raise_only():
    from app.services.review import _apply_overrides
    fs = [_f(cwe_id="CWE-89", severity="medium"), _f(cwe_id="CWE-1", severity="critical")]
    _apply_overrides(fs, {"CWE-89": "critical", "CWE-1": "low"})
    assert fs[0].severity == "critical"   # raised
    assert fs[1].severity == "critical"   # never lowered


def test_noise_filter_keeps_verified():
    from app.services.review import _filter_noise
    fs = [_f(confidence="LOW", verified=False), _f(confidence="LOW", verified=True),
          _f(confidence="HIGH", verified=False)]
    kept = _filter_noise(fs, "MEDIUM")
    assert len(kept) == 2  # drops the unverified LOW; keeps verified-LOW and HIGH


def test_config_semgrep_passthrough():
    from app.core.config_file import parse_config
    cfg = parse_config('semgrep_config: "p/owasp-top-ten"')
    assert cfg.semgrep_config == "p/owasp-top-ten"
    assert parse_config("version: 1").semgrep_config == ""  # default empty


def test_llm_backend_ordering(monkeypatch):
    from app.config import get_settings
    from app.services import llm
    monkeypatch.setenv("GEMINI_API_KEY", "AIzareal1")
    monkeypatch.setenv("GEMINI_2", "AIzareal2")
    monkeypatch.setenv("GEMINI_API_KEY_3", "AIzareal3")
    monkeypatch.setenv("GROQ_API_KEY_1", "gsk_real")
    get_settings.cache_clear()
    bs = llm._backends()
    assert [b.provider for b in bs] == ["gemini", "gemini", "gemini", "groq"]
    assert llm.available() is True
    get_settings.cache_clear()


def test_llm_no_backend_returns_none():
    # conftest clears all keys → no backends → complete_json returns None (graceful).
    from app.services import llm
    assert llm.available() is False
    assert llm.complete_json("sys", "prompt") is None


def test_critic_keyless_keeps_all():
    # No Gemini key → critic returns findings unchanged (graceful).
    from app.agents.analysis import critic
    fs = [_f(verified=False, source="security-agent")]
    assert critic("some diff", fs) == fs


def test_finding_default_status_open():
    f = _f()
    assert f.status == "open"


def test_triage_persists_via_store():
    r = Review(id="triage1", repo="o/r", pr_number=3, status="completed",
               findings=[_f(), _f(file="b.py")], created_at="2026-06-27T00:00:00Z")
    store.save_review(r)
    got = store.get_review("triage1")
    got.findings[1].status = "false_positive"
    store.save_review(got)
    again = store.get_review("triage1")
    assert again.findings[0].status == "open"
    assert again.findings[1].status == "false_positive"


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

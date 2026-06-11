"""Composite pull-request risk score (proposal Appendix B), lean variant.

    R = w1*S_sast + w2*S_sca + w3*S_secrets + w4*S_context

History factor is fixed at 1.0 in this MVP (no longitudinal profile store yet);
the formula is kept intact so profiling can be added without changing callers.
"""
from app.models import Finding

W_SAST, W_SCA, W_SECRETS, W_CONTEXT = 0.40, 0.25, 0.25, 0.10

# Sources that contribute to the code-security (SAST) dimension. Includes the
# LLM code agents so the dimension is still meaningful when no scanner is installed.
CODE_SOURCES = {"semgrep", "bandit", "security-agent", "logic-agent"}

# File-path keywords → sensitivity factor (general 1.0, auth 1.5, crypto/payment 2.0).
_SENSITIVE_HIGH = ("crypto", "payment", "billing", "keystore", "private_key", "secret")
_SENSITIVE_MED = ("auth", "login", "session", "password", "token", "permission")


def _clamp(x: float, lo: float = 0.0, hi: float = 10.0) -> float:
    return max(lo, min(hi, x))


def sensitivity_factor(files: list[str]) -> float:
    blob = " ".join(files).lower()
    if any(k in blob for k in _SENSITIVE_HIGH):
        return 2.0
    if any(k in blob for k in _SENSITIVE_MED):
        return 1.5
    return 1.0


def compute_risk(findings: list[Finding], changed_files: list[str]) -> tuple[float, dict]:
    """Return (risk_score 0-10, component breakdown). Each dimension is driven by
    its most severe finding (max CVSS), so one critical issue is not diluted."""
    code = [f for f in findings if f.source in CODE_SOURCES]
    s_sast = _clamp(max((f.cvss_estimate for f in code), default=0.0))

    sca = [f for f in findings if f.source == "trivy"]
    s_sca = _clamp(max((f.cvss_estimate for f in sca), default=0.0))

    secrets = [f for f in findings if f.source == "gitleaks"]
    if any(f.verified for f in secrets):
        s_secrets = 10.0
    elif secrets:
        s_secrets = 5.0
    else:
        s_secrets = 0.0

    history_factor = 1.0  # placeholder for longitudinal profiling
    s_context = _clamp((sensitivity_factor(changed_files) * history_factor - 1.0) * 5.0)

    score = W_SAST * s_sast + W_SCA * s_sca + W_SECRETS * s_secrets + W_CONTEXT * s_context
    breakdown = {
        "S_sast": round(s_sast, 2),
        "S_sca": round(s_sca, 2),
        "S_secrets": round(s_secrets, 2),
        "S_context": round(s_context, 2),
    }
    return round(score, 2), breakdown


def should_gate(findings: list[Finding], score: float, threshold: float) -> tuple[bool, str]:
    """Decide whether to block the merge, and why.

    A blended score is useful for trend, but a security gate must hard-block on a
    single critical issue regardless of how the average washes out.
    """
    if any(f.severity == "critical" for f in findings):
        return True, "a CRITICAL finding is present"
    if any(f.severity == "high" and f.verified for f in findings):
        return True, "a verified HIGH-severity finding is present"
    if score >= threshold:
        return True, f"composite risk {score} ≥ gate threshold {threshold}"
    return False, "within policy"

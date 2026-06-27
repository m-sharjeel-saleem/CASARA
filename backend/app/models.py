"""Domain models shared across the pipeline and the API."""
from typing import Literal

from pydantic import BaseModel, Field

Severity = Literal["info", "low", "medium", "high", "critical"]
Confidence = Literal["LOW", "MEDIUM", "HIGH"]
ReviewStatus = Literal["pending", "running", "completed", "failed"]
TriageStatus = Literal["open", "ignored", "false_positive", "fixed"]

# Which scanner sources count toward the SAST dimension of the risk score.
SAST_SOURCES = {"semgrep", "bandit"}


class Finding(BaseModel):
    source: str                      # scanner or agent name, e.g. "semgrep", "security-agent"
    file: str = ""
    line: int | None = None
    cwe_id: str = ""
    severity: Severity = "medium"
    cvss_estimate: float = 0.0
    message: str = ""
    fix_prompt: str = ""
    confidence: Confidence = "MEDIUM"
    verified: bool = False            # confirmed by >=2 sources (deterministic + agent)
    ai_signal: str = ""               # why this looks AI-generated (set by the ai-code agent)
    status: TriageStatus = "open"     # triage state, editable from the dashboard
    priority: int = 0                 # 0-100 real-world priority (set by the triage agent)
    exploitability: str = ""          # high|medium|low|noise (set by the triage agent)
    epss: float = 0.0                 # EPSS exploit-probability (0-1) for CVE findings


class Review(BaseModel):
    id: str
    repo: str
    pr_number: int
    installation_id: int | None = None   # GitHub App installation (the tenant); None in PAT mode
    pr_title: str = ""
    author: str = ""
    head_sha: str = ""
    status: ReviewStatus = "pending"
    risk_score: float = 0.0
    gated: bool = False
    summary: str = ""
    findings: list[Finding] = Field(default_factory=list)
    created_at: str = ""
    completed_at: str | None = None

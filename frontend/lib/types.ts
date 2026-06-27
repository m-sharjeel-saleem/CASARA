export type Severity = "info" | "low" | "medium" | "high" | "critical";

export interface Finding {
  source: string;
  file: string;
  line: number | null;
  cwe_id: string;
  severity: Severity;
  cvss_estimate: number;
  message: string;
  fix_prompt: string;
  confidence: "LOW" | "MEDIUM" | "HIGH";
  verified: boolean;
  ai_signal: string;
  status: TriageStatus;
  priority: number;
  exploitability: string;
  epss: number;
}

export type TriageStatus = "open" | "ignored" | "false_positive" | "fixed";

export interface Review {
  id: string;
  repo: string;
  pr_number: number;
  installation_id: number | null;
  pr_title: string;
  author: string;
  head_sha: string;
  status: "pending" | "running" | "completed" | "failed";
  risk_score: number;
  gated: boolean;
  summary: string;
  findings: Finding[];
  created_at: string;
  completed_at: string | null;
}

export interface Stats {
  total_reviews: number;
  gated_count: number;
  avg_risk: number;
  total_findings: number;
}

export interface Installation {
  id: number;
  account: string;
  account_type: string;
  repo_count: number;
  created_at: string;
  suspended?: boolean;
}

export interface PathRule {
  path: string;
  instructions: string;
  severity: Severity | null;
}

export interface CasaraConfig {
  version: number;
  languages: string[];
  rules: PathRule[];
  gate: { level: "off" | "warning" | "error"; threshold: number };
  noise: { max_comments: number; min_confidence: "LOW" | "MEDIUM" | "HIGH" };
  severity_overrides: Record<string, Severity>;
  semgrep_config: string;
}

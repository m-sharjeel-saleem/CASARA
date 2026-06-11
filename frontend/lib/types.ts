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
}

export interface Review {
  id: string;
  repo: string;
  pr_number: number;
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

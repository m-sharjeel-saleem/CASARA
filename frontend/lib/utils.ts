import { clsx, type ClassValue } from "clsx";
import { twMerge } from "tailwind-merge";

import type { Finding, Review, Severity } from "./types";

export function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs));
}

export function riskColor(score: number): string {
  if (score >= 7) return "text-sev-critical";
  if (score >= 4) return "text-sev-medium";
  return "text-safe";
}

export function riskHex(score: number): string {
  if (score >= 7) return "#ff4d6d";
  if (score >= 4) return "#f5c043";
  return "#3ee0a3";
}

export const SEV_ORDER: Severity[] = ["critical", "high", "medium", "low", "info"];

export const SEV_HEX: Record<Severity, string> = {
  critical: "#ff4d6d",
  high: "#ff8a3d",
  medium: "#f5c043",
  low: "#7c8aa3",
  info: "#5b6678",
};

export const SEV_RANK: Record<Severity, number> = {
  critical: 4, high: 3, medium: 2, low: 1, info: 0,
};

export function timeAgo(iso: string): string {
  if (!iso) return "";
  const diff = (Date.now() - new Date(iso).getTime()) / 1000;
  if (diff < 60) return "just now";
  if (diff < 3600) return `${Math.floor(diff / 60)}m ago`;
  if (diff < 86400) return `${Math.floor(diff / 3600)}h ago`;
  return `${Math.floor(diff / 86400)}d ago`;
}

/** Count findings by severity across a set of reviews. */
export function severityCounts(reviews: Review[]): Record<Severity, number> {
  const c: Record<Severity, number> = { critical: 0, high: 0, medium: 0, low: 0, info: 0 };
  for (const r of reviews) for (const f of r.findings) c[f.severity] = (c[f.severity] ?? 0) + 1;
  return c;
}

/** Highest-severity finding in a review (drives the card stripe). */
export function topSeverity(findings: Finding[]): Severity | null {
  let top: Severity | null = null;
  for (const f of findings) {
    if (top === null || SEV_RANK[f.severity] > SEV_RANK[top]) top = f.severity;
  }
  return top;
}

/** Group findings by severity, ordered critical→info. */
export function groupBySeverity(findings: Finding[]): [Severity, Finding[]][] {
  const groups = new Map<Severity, Finding[]>();
  for (const f of findings) {
    if (!groups.has(f.severity)) groups.set(f.severity, []);
    groups.get(f.severity)!.push(f);
  }
  return SEV_ORDER.filter((s) => groups.has(s)).map((s) => [s, groups.get(s)!]);
}

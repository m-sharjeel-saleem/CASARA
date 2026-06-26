"use client";

import {
  ArrowLeft, BadgeCheck, Bot, Check, Copy, ExternalLink, GitPullRequest,
  ShieldAlert, ShieldCheck, Wrench,
} from "lucide-react";
import Link from "next/link";
import { useParams } from "next/navigation";
import { useState } from "react";
import ReactMarkdown from "react-markdown";

import { PageHeader } from "@/components/PageHeader";
import { RiskGauge } from "@/components/charts";
import { api } from "@/lib/api";
import { useReview } from "@/lib/hooks";
import type { Finding, Severity, TriageStatus } from "@/lib/types";
import { cn, cweUrl, findingCategory, SEV_HEX, SEV_RANK, timeAgo } from "@/lib/utils";

const TRIAGE: { value: TriageStatus; label: string }[] = [
  { value: "open", label: "Open" },
  { value: "ignored", label: "Ignored" },
  { value: "false_positive", label: "False positive" },
  { value: "fixed", label: "Fixed" },
];
const TRIAGE_STYLE: Record<TriageStatus, string> = {
  open: "text-slate-400 border-border",
  ignored: "text-slate-500 border-border",
  false_positive: "text-warn border-warn/30",
  fixed: "text-safe border-safe/30",
};

function SevPill({ s }: { s: Severity }) {
  return (
    <span className="rounded-full border px-2 py-0.5 text-[10px] font-semibold uppercase tracking-wide"
      style={{ color: SEV_HEX[s], borderColor: `${SEV_HEX[s]}55`, background: `${SEV_HEX[s]}14` }}>
      {s}
    </span>
  );
}

function FindingDetail({ f, idx, reviewId, onTriaged }: {
  f: Finding; idx: number; reviewId: string; onTriaged: () => void;
}) {
  const [copied, setCopied] = useState(false);
  const [busy, setBusy] = useState(false);
  const cwe = cweUrl(f.cwe_id);
  const dimmed = f.status === "ignored" || f.status === "false_positive";
  const copyFix = () => {
    navigator.clipboard?.writeText(f.fix_prompt).then(() => {
      setCopied(true); setTimeout(() => setCopied(false), 2000);
    });
  };
  const triage = async (status: TriageStatus) => {
    setBusy(true);
    try { await api.triageFinding(reviewId, idx, status); onTriaged(); }
    finally { setBusy(false); }
  };
  return (
    <div className={cn("panel rounded-xl p-4 transition-opacity",
      { critical: "stripe-critical", high: "stripe-high", medium: "stripe-medium", low: "stripe-low", info: "stripe-low" }[f.severity],
      dimmed && "opacity-55")}>
      <div className="flex flex-wrap items-center gap-2">
        <SevPill s={f.severity} />
        <span className="rounded-full border border-border bg-white/[0.03] px-2 py-0.5 text-[10px] text-slate-400">
          {findingCategory(f)}
        </span>
        {cwe ? (
          <a href={cwe} target="_blank" rel="noopener noreferrer"
            className="inline-flex items-center gap-1 font-mono text-[11px] text-accent-soft hover:text-white">
            {f.cwe_id} <ExternalLink className="h-3 w-3" />
          </a>
        ) : f.cwe_id ? <span className="font-mono text-[11px] text-slate-500">{f.cwe_id}</span> : null}
        {f.verified ? (
          <span className="inline-flex items-center gap-1 text-[11px] text-safe"><BadgeCheck className="h-3.5 w-3.5" /> verified</span>
        ) : (
          <span className="text-[11px] text-slate-600">{f.confidence.toLowerCase()} confidence</span>
        )}
        {f.ai_signal && (
          <span className="inline-flex items-center gap-1 rounded-full border border-accent/30 bg-accent/10 px-2 py-0.5 text-[10px] text-accent-soft">
            <Bot className="h-3 w-3" /> {f.ai_signal}
          </span>
        )}
        <span className="ml-auto font-mono text-[11px] text-slate-500">via {f.source}</span>
      </div>

      <code className="mt-3 block font-mono text-[12px] text-slate-300">
        {f.file}{f.line ? `:${f.line}` : ""}
      </code>
      <p className="mt-2 text-[14px] leading-relaxed text-slate-200">{f.message}</p>

      {f.fix_prompt && (
        <div className="mt-3 rounded-lg border border-border bg-black/30 p-3">
          <div className="mb-1.5 flex items-center justify-between">
            <span className="inline-flex items-center gap-1.5 text-[11px] font-semibold text-safe">
              <Wrench className="h-3.5 w-3.5" /> Suggested fix
            </span>
            <button onClick={copyFix} className="inline-flex items-center gap-1 text-[11px] text-slate-400 hover:text-white">
              {copied ? <><Check className="h-3 w-3 text-safe" /> Copied</> : <><Copy className="h-3 w-3" /> Copy</>}
            </button>
          </div>
          <p className="text-[13px] leading-relaxed text-slate-300">{f.fix_prompt}</p>
        </div>
      )}

      <div className="mt-3 flex items-center gap-1.5 border-t border-border/60 pt-3">
        <span className="text-[11px] text-slate-500">Triage:</span>
        {TRIAGE.map((t) => (
          <button key={t.value} disabled={busy} onClick={() => triage(t.value)}
            className={cn("rounded-full border px-2.5 py-0.5 text-[11px] transition disabled:opacity-50",
              f.status === t.value ? cn(TRIAGE_STYLE[t.value], "bg-white/[0.04] font-medium")
                : "border-transparent text-slate-500 hover:text-slate-300")}>
            {t.label}
          </button>
        ))}
      </div>
    </div>
  );
}

export default function ReviewDetail() {
  const { id } = useParams<{ id: string }>();
  const { data: review, isLoading, error, mutate } = useReview(id);
  const [hideResolved, setHideResolved] = useState(false);

  if (isLoading) {
    return <><div className="skeleton mb-6 h-10 w-64 rounded" /><div className="space-y-3">{[0, 1, 2].map(i => <div key={i} className="skeleton h-28 rounded-2xl" />)}</div></>;
  }
  if (error || !review) {
    return (
      <div className="panel rounded-2xl py-16 text-center">
        <p className="text-sm text-slate-400">Review not found.</p>
        <Link href="/dashboard/reviews" className="mt-3 inline-block text-xs text-accent-soft">← Back to reviews</Link>
      </div>
    );
  }

  // Preserve each finding's original index (needed for triage), then group by severity.
  const indexed = review.findings.map((f, idx) => ({ f, idx }))
    .filter(({ f }) => !hideResolved || (f.status !== "ignored" && f.status !== "false_positive" && f.status !== "fixed"));
  const bySev = new Map<Severity, { f: Finding; idx: number }[]>();
  for (const item of indexed) {
    if (!bySev.has(item.f.severity)) bySev.set(item.f.severity, []);
    bySev.get(item.f.severity)!.push(item);
  }
  const groups = [...bySev.entries()].sort((a, b) => SEV_RANK[b[0]] - SEV_RANK[a[0]]);
  const resolvedCount = review.findings.filter(
    (f) => f.status === "ignored" || f.status === "false_positive" || f.status === "fixed").length;

  return (
    <>
      <Link href="/dashboard/reviews" className="mb-4 inline-flex items-center gap-1.5 text-xs text-slate-400 hover:text-white">
        <ArrowLeft className="h-3.5 w-3.5" /> All reviews
      </Link>

      <PageHeader eyebrow="Review detail" title={review.pr_title || "Pull request"} />

      {/* Summary card */}
      <div className="panel mb-6 flex flex-col gap-5 rounded-2xl p-5 sm:flex-row sm:items-center">
        <RiskGauge score={review.risk_score} size={96} />
        <div className="min-w-0 flex-1">
          <div className="flex flex-wrap items-center gap-2 text-sm">
            <GitPullRequest className="h-4 w-4 text-slate-500" />
            <span className="font-mono text-slate-300">{review.repo}</span>
            <span className="text-slate-600">#{review.pr_number}</span>
            {review.gated
              ? <span className="inline-flex items-center gap-1 rounded-full border border-sev-critical/30 bg-sev-critical/10 px-2.5 py-1 text-[11px] font-medium text-sev-critical"><ShieldAlert className="h-3 w-3" /> Blocked</span>
              : <span className="inline-flex items-center gap-1 rounded-full border border-safe/30 bg-safe/10 px-2.5 py-1 text-[11px] font-medium text-safe"><ShieldCheck className="h-3 w-3" /> Passed</span>}
          </div>
          <div className="mt-1 text-[11px] text-slate-500">
            {review.author && `@${review.author} · `}{review.findings.length} findings · {timeAgo(review.created_at)}
          </div>
          {review.summary && (
            <div className="prose prose-invert prose-sm mt-3 max-w-none text-slate-300">
              <ReactMarkdown>{review.summary}</ReactMarkdown>
            </div>
          )}
        </div>
      </div>

      {/* Findings grouped by severity */}
      {review.findings.length === 0 ? (
        <div className="panel rounded-2xl py-12 text-center text-sm text-slate-500">No findings in this review.</div>
      ) : (
        <>
          {resolvedCount > 0 && (
            <label className="mb-4 inline-flex cursor-pointer items-center gap-2 text-xs text-slate-400">
              <input type="checkbox" checked={hideResolved} onChange={(e) => setHideResolved(e.target.checked)}
                className="accent-accent" />
              Hide resolved ({resolvedCount} ignored / false-positive / fixed)
            </label>
          )}
          <div className="space-y-6">
            {groups.map(([s, items]) => (
              <section key={s}>
                <div className="mb-2.5 flex items-center gap-2">
                  <SevPill s={s} />
                  <span className="font-mono text-[11px] text-slate-500">{items.length} finding{items.length > 1 ? "s" : ""}</span>
                </div>
                <div className="space-y-3">
                  {items.map(({ f, idx }) => (
                    <FindingDetail key={idx} f={f} idx={idx} reviewId={review.id} onTriaged={() => mutate()} />
                  ))}
                </div>
              </section>
            ))}
          </div>
        </>
      )}
    </>
  );
}

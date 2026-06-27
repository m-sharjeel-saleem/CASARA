"use client";

import { motion } from "framer-motion";
import {
  BadgeCheck, Bot, ChevronDown, ExternalLink, GitPullRequest, Loader2, ShieldAlert, ShieldCheck, Wrench,
} from "lucide-react";
import Link from "next/link";
import { useState } from "react";
import ReactMarkdown from "react-markdown";

import type { Finding, Review, Severity } from "@/lib/types";
import { cn, gradeForRisk, gradeHex, groupBySeverity, isAudit, riskColor, SEV_HEX, timeAgo, topSeverity } from "@/lib/utils";

const stripeClass: Record<Severity, string> = {
  critical: "stripe-critical", high: "stripe-high", medium: "stripe-medium",
  low: "stripe-low", info: "stripe-low",
};

function SevPill({ s }: { s: Severity }) {
  return (
    <span
      className="rounded-full border px-2 py-0.5 text-[10px] font-semibold uppercase tracking-wide"
      style={{ color: SEV_HEX[s], borderColor: `${SEV_HEX[s]}55`, background: `${SEV_HEX[s]}14` }}
    >
      {s}
    </span>
  );
}

function FindingRow({ f }: { f: Finding }) {
  return (
    <div className={cn("rounded-lg border border-border bg-white/[0.02] p-3", stripeClass[f.severity])}>
      <div className="flex flex-wrap items-center gap-2">
        <SevPill s={f.severity} />
        <code className="font-mono text-[11px] text-accent-soft">{f.file}{f.line ? `:${f.line}` : ""}</code>
        {f.cwe_id && <span className="font-mono text-[11px] text-slate-500">{f.cwe_id}</span>}
        <span className="text-[11px] text-slate-600">via {f.source}</span>
        {f.verified ? (
          <span className="inline-flex items-center gap-1 text-[11px] text-safe">
            <BadgeCheck className="h-3.5 w-3.5" /> verified
          </span>
        ) : (
          <span className="text-[11px] text-slate-600">{f.confidence.toLowerCase()} confidence</span>
        )}
        {f.ai_signal && (
          <span className="inline-flex items-center gap-1 rounded-full border border-accent/30 bg-accent/10 px-2 py-0.5 text-[10px] text-accent-soft">
            <Bot className="h-3 w-3" /> {f.ai_signal}
          </span>
        )}
      </div>
      <p className="mt-2 text-[13px] leading-relaxed text-slate-300">{f.message}</p>
      {f.fix_prompt && (
        <p className="mt-2 flex gap-1.5 rounded-md bg-black/30 px-2.5 py-2 text-[12px] text-slate-400">
          <Wrench className="mt-0.5 h-3.5 w-3.5 shrink-0 text-safe" />
          <span><span className="text-safe">Fix —</span> {f.fix_prompt}</span>
        </p>
      )}
    </div>
  );
}

export function ReviewCard({ review, index = 0 }: { review: Review; index?: number }) {
  const [open, setOpen] = useState(false);
  const running = review.status === "running" || review.status === "pending";
  const failed = review.status === "failed";
  const top = topSeverity(review.findings);
  const groups = groupBySeverity(review.findings);

  return (
    <motion.div
      initial={{ opacity: 0, y: 10 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ delay: Math.min(index * 0.04, 0.3) }}
      className={cn("panel lift overflow-hidden rounded-2xl", top && stripeClass[top])}
    >
      <button onClick={() => setOpen((o) => !o)} className="flex w-full items-center gap-4 p-4 text-left">
        <div className={cn("grid h-11 w-11 shrink-0 place-items-center rounded-xl border",
          failed ? "border-border bg-white/5 text-slate-400"
          : review.gated ? "border-sev-critical/30 bg-sev-critical/10 text-sev-critical"
          : "border-safe/30 bg-safe/10 text-safe")}>
          {running ? <Loader2 className="h-5 w-5 animate-spin text-accent-soft" />
            : review.gated ? <ShieldAlert className="h-5 w-5" /> : <ShieldCheck className="h-5 w-5" />}
        </div>

        <div className="min-w-0 flex-1">
          <div className="flex items-center gap-2 text-sm">
            <GitPullRequest className="h-3.5 w-3.5 shrink-0 text-slate-500" />
            <span className="font-mono text-slate-400">{review.repo}</span>
            {isAudit(review.pr_number)
              ? <span className="rounded border border-accent/30 bg-accent/10 px-1.5 py-0.5 text-[9px] font-semibold uppercase tracking-wide text-accent-soft">Audit</span>
              : <span className="text-slate-600">#{review.pr_number}</span>}
          </div>
          <div className="mt-0.5 truncate text-[15px] font-medium text-slate-100">
            {review.pr_title || "Pull request"}
          </div>
          <div className="mt-1 flex flex-wrap items-center gap-1.5 text-[11px] text-slate-500">
            {review.author && <span>@{review.author}</span>}
            <span>·</span>
            <span className="tnum">{review.findings.length} findings</span>
            <span>·</span>
            <span>{timeAgo(review.created_at)}</span>
            {groups.slice(0, 3).map(([s, items]) => (
              <span key={s} className="inline-flex items-center gap-1">
                <span className="h-1.5 w-1.5 rounded-sm" style={{ background: SEV_HEX[s] }} />
                <span className="tnum">{items.length}</span>
              </span>
            ))}
          </div>
        </div>

        <div className="flex shrink-0 items-center gap-3">
          {isAudit(review.pr_number) && review.status === "completed" && (
            <div className="grid h-10 w-10 place-items-center rounded-xl border font-display text-lg font-bold"
              style={{ color: gradeHex(gradeForRisk(review.risk_score)),
                borderColor: `${gradeHex(gradeForRisk(review.risk_score))}55`,
                background: `${gradeHex(gradeForRisk(review.risk_score))}14` }}>
              {gradeForRisk(review.risk_score)}
            </div>
          )}
          <div className="text-right">
            <div className={cn("font-mono text-xl font-bold tnum", riskColor(review.risk_score))}>
              {review.risk_score.toFixed(1)}
            </div>
            <div className="eyebrow !text-[8px]">risk</div>
          </div>
          {failed ? (
            <span className="rounded-full border border-border bg-white/5 px-2.5 py-1 text-[11px] text-slate-400">Failed</span>
          ) : review.gated ? (
            <span className="rounded-full border border-sev-critical/30 bg-sev-critical/10 px-2.5 py-1 text-[11px] font-medium text-sev-critical">Blocked</span>
          ) : (
            <span className="rounded-full border border-safe/30 bg-safe/10 px-2.5 py-1 text-[11px] font-medium text-safe">Passed</span>
          )}
          <ChevronDown className={cn("h-4 w-4 text-slate-500 transition-transform", open && "rotate-180")} />
        </div>
      </button>

      {open && (
        <div className="border-t border-border px-4 pb-4 pt-3">
          <div className="mb-3 flex justify-end">
            <Link href={`/dashboard/reviews/${review.id}`}
              className="inline-flex items-center gap-1 text-[11px] text-accent-soft hover:text-white">
              Full detail & triage <ExternalLink className="h-3 w-3" />
            </Link>
          </div>
          {review.summary && (
            <div className="prose prose-invert prose-sm mb-4 max-w-none text-slate-300">
              <ReactMarkdown>{review.summary}</ReactMarkdown>
            </div>
          )}
          {review.findings.length === 0 ? (
            <p className="text-sm text-slate-500">No findings.</p>
          ) : (
            <div className="space-y-4">
              {groups.map(([s, items]) => (
                <div key={s}>
                  <div className="mb-2 flex items-center gap-2">
                    <SevPill s={s} />
                    <span className="text-[11px] text-slate-500 tnum">{items.length}</span>
                  </div>
                  <div className="space-y-2">
                    {items.map((f, i) => <FindingRow key={i} f={f} />)}
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>
      )}
    </motion.div>
  );
}

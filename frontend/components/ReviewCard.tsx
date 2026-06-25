"use client";

import { motion } from "framer-motion";
import { BadgeCheck, Bot, ChevronDown, GitPullRequest, Loader2, ShieldAlert, ShieldCheck } from "lucide-react";
import { useState } from "react";
import ReactMarkdown from "react-markdown";

import type { Finding, Review, Severity } from "@/lib/types";
import { cn, riskColor, timeAgo } from "@/lib/utils";

const sevStyle: Record<Severity, string> = {
  critical: "bg-red-500/15 text-red-300 border-red-500/30",
  high: "bg-orange-500/15 text-orange-300 border-orange-500/30",
  medium: "bg-amber-500/15 text-amber-300 border-amber-500/30",
  low: "bg-zinc-500/15 text-zinc-300 border-zinc-500/30",
  info: "bg-zinc-500/15 text-zinc-400 border-zinc-500/30",
};

function FindingRow({ f }: { f: Finding }) {
  return (
    <div className="rounded-lg border border-border bg-white/[0.02] p-3">
      <div className="flex flex-wrap items-center gap-2">
        <span className={cn("rounded-full border px-2 py-0.5 text-[11px] font-medium", sevStyle[f.severity])}>
          {f.severity.toUpperCase()}
        </span>
        <code className="font-mono text-[11px] text-accent-soft">{f.file}{f.line ? `:${f.line}` : ""}</code>
        {f.cwe_id && <span className="text-[11px] text-zinc-500">{f.cwe_id}</span>}
        <span className="text-[11px] text-zinc-600">via {f.source}</span>
        {f.verified && (
          <span className="inline-flex items-center gap-1 text-[11px] text-safe">
            <BadgeCheck className="h-3.5 w-3.5" /> verified
          </span>
        )}
        {!f.verified && (
          <span className="text-[11px] text-zinc-600">{f.confidence.toLowerCase()} confidence</span>
        )}
        {f.ai_signal && (
          <span className="inline-flex items-center gap-1 rounded-full border border-accent/30 bg-accent/10 px-2 py-0.5 text-[11px] text-accent-soft">
            <Bot className="h-3 w-3" /> {f.ai_signal}
          </span>
        )}
      </div>
      <p className="mt-1.5 text-[13px] text-zinc-300">{f.message}</p>
      {f.fix_prompt && (
        <p className="mt-1.5 rounded bg-black/30 px-2 py-1.5 text-[12px] text-zinc-400">
          <span className="text-safe">Fix:</span> {f.fix_prompt}
        </p>
      )}
    </div>
  );
}

export function ReviewCard({ review }: { review: Review }) {
  const [open, setOpen] = useState(false);
  const running = review.status === "running" || review.status === "pending";

  return (
    <motion.div
      initial={{ opacity: 0, y: 8 }}
      animate={{ opacity: 1, y: 0 }}
      className="glass overflow-hidden rounded-2xl"
    >
      <button onClick={() => setOpen((o) => !o)} className="flex w-full items-center gap-4 p-4 text-left">
        <div className={cn("grid h-10 w-10 shrink-0 place-items-center rounded-xl",
          review.gated ? "bg-danger/15 text-danger" : "bg-safe/15 text-safe")}>
          {running ? <Loader2 className="h-5 w-5 animate-spin text-accent-soft" />
            : review.gated ? <ShieldAlert className="h-5 w-5" /> : <ShieldCheck className="h-5 w-5" />}
        </div>

        <div className="min-w-0 flex-1">
          <div className="flex items-center gap-2 text-sm">
            <GitPullRequest className="h-3.5 w-3.5 shrink-0 text-zinc-500" />
            <span className="font-mono text-zinc-400">{review.repo}</span>
            <span className="text-zinc-600">#{review.pr_number}</span>
          </div>
          <div className="mt-0.5 truncate text-[15px] font-medium text-zinc-100">
            {review.pr_title || "Pull request"}
          </div>
          <div className="mt-0.5 text-[11px] text-zinc-500">
            {review.author && `@${review.author} · `}{review.findings.length} findings · {timeAgo(review.created_at)}
          </div>
        </div>

        <div className="flex shrink-0 items-center gap-3">
          <div className="text-right">
            <div className={cn("font-mono text-xl font-bold", riskColor(review.risk_score))}>
              {review.risk_score.toFixed(1)}
            </div>
            <div className="text-[10px] uppercase tracking-wide text-zinc-600">risk /10</div>
          </div>
          {review.gated
            ? <span className="rounded-full border border-danger/30 bg-danger/10 px-2.5 py-1 text-[11px] font-medium text-danger">Blocked</span>
            : <span className="rounded-full border border-safe/30 bg-safe/10 px-2.5 py-1 text-[11px] font-medium text-safe">Passed</span>}
          <ChevronDown className={cn("h-4 w-4 text-zinc-500 transition-transform", open && "rotate-180")} />
        </div>
      </button>

      {open && (
        <div className="border-t border-border px-4 pb-4 pt-3">
          {review.summary && (
            <div className="prose prose-invert prose-sm mb-3 max-w-none text-zinc-300">
              <ReactMarkdown>{review.summary}</ReactMarkdown>
            </div>
          )}
          <div className="space-y-2">
            {review.findings.length === 0
              ? <p className="text-sm text-zinc-500">No findings.</p>
              : review.findings.map((f, i) => <FindingRow key={i} f={f} />)}
          </div>
        </div>
      )}
    </motion.div>
  );
}

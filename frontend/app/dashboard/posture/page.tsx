"use client";

import { ArrowRight, FolderGit2 } from "lucide-react";
import Link from "next/link";
import { useMemo } from "react";

import { PageHeader } from "@/components/PageHeader";
import { GradeRing, PostureHero } from "@/components/Posture";
import { useLiveFeed, useReviews } from "@/lib/hooks";
import type { Finding, Review, Severity } from "@/lib/types";
import { cn, cweUrl, gradeForRisk, gradeHex, SEV_HEX, SEV_RANK } from "@/lib/utils";

export default function PosturePage() {
  const { data: reviews = [], isLoading } = useReviews();
  useLiveFeed();

  const repos = useMemo(() => {
    const map = new Map<string, { repo: string; n: number; findings: number; sum: number }>();
    for (const r of reviews.filter((x) => x.status === "completed")) {
      const e = map.get(r.repo) ?? { repo: r.repo, n: 0, findings: 0, sum: 0 };
      e.n += 1; e.findings += r.findings.length; e.sum += r.risk_score;
      map.set(r.repo, e);
    }
    return [...map.values()].map((e) => ({ repo: e.repo, findings: e.findings, avg: e.sum / e.n }))
      .sort((a, b) => b.avg - a.avg);
  }, [reviews]);

  const topRisks = useMemo(() => {
    const out: { f: Finding; review: Review }[] = [];
    for (const r of reviews) for (const f of r.findings) out.push({ f, review: r });
    return out.sort((a, b) => SEV_RANK[b.f.severity] - SEV_RANK[a.f.severity]).slice(0, 8);
  }, [reviews]);

  if (isLoading) {
    return <><PageHeader eyebrow="Posture" title="Security posture" /><div className="skeleton h-56 rounded-3xl" /></>;
  }

  return (
    <>
      <PageHeader eyebrow="Posture" title="Security posture" />

      <PostureHero reviews={reviews} />

      {/* Per-repo posture grid */}
      <section className="mt-7">
        <h2 className="eyebrow mb-3">Repositories by posture</h2>
        {repos.length === 0 ? (
          <div className="panel rounded-2xl py-12 text-center text-sm text-slate-500">
            No reviewed repositories yet — run an audit from the Repositories tab.
          </div>
        ) : (
          <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
            {repos.map((r) => {
              const grade = gradeForRisk(r.avg);
              return (
                <div key={r.repo} className="panel lift flex items-center gap-4 rounded-2xl p-5">
                  <GradeRing grade={grade} score={r.avg} size={84} />
                  <div className="min-w-0">
                    <div className="flex items-center gap-1.5 text-[13px] font-medium text-slate-200">
                      <FolderGit2 className="h-3.5 w-3.5 shrink-0 text-slate-500" />
                      <span className="truncate font-mono">{r.repo.split("/").pop()}</span>
                    </div>
                    <div className="mt-0.5 truncate font-mono text-[11px] text-slate-500">{r.repo}</div>
                    <div className="mt-1.5 text-[12px] text-slate-400">
                      <span className="font-mono tnum" style={{ color: gradeHex(grade) }}>{r.avg.toFixed(1)}</span> avg risk · {r.findings} findings
                    </div>
                  </div>
                </div>
              );
            })}
          </div>
        )}
      </section>

      {/* Top risks */}
      <section className="mt-7">
        <h2 className="eyebrow mb-3">Top risks to remediate</h2>
        {topRisks.length === 0 ? (
          <div className="panel rounded-2xl py-12 text-center text-sm text-slate-500">No findings yet.</div>
        ) : (
          <div className="space-y-2">
            {topRisks.map(({ f, review }, i) => {
              const cwe = cweUrl(f.cwe_id);
              return (
                <Link key={i} href={`/dashboard/reviews/${review.id}`}
                  className={cn("panel lift flex items-center gap-3 rounded-xl px-4 py-3",
                    { critical: "stripe-critical", high: "stripe-high", medium: "stripe-medium", low: "stripe-low", info: "stripe-low" }[f.severity])}>
                  <span className="rounded-full border px-2 py-0.5 text-[10px] font-semibold uppercase tracking-wide"
                    style={{ color: SEV_HEX[f.severity as Severity], borderColor: `${SEV_HEX[f.severity as Severity]}55`, background: `${SEV_HEX[f.severity as Severity]}14` }}>
                    {f.severity}
                  </span>
                  <span className="min-w-0 flex-1 truncate text-[13px] text-slate-200">{f.message}</span>
                  {f.cwe_id && <span className="hidden font-mono text-[11px] text-slate-500 sm:inline">{f.cwe_id}</span>}
                  <span className="hidden truncate font-mono text-[11px] text-slate-600 md:inline">{f.file.split("/").pop()}</span>
                  <ArrowRight className="h-3.5 w-3.5 shrink-0 text-slate-600" />
                </Link>
              );
            })}
          </div>
        )}
      </section>
    </>
  );
}

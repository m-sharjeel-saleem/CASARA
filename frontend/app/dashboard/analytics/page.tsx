"use client";

import { useMemo } from "react";

import { BarList, Sparkline, SeverityBar } from "@/components/charts";
import { PageHeader } from "@/components/PageHeader";
import { useLiveFeed, useReviews } from "@/lib/hooks";
import type { Finding } from "@/lib/types";
import { countBy, findingCategory, severityCounts } from "@/lib/utils";

function Panel({ title, children }: { title: string; children: React.ReactNode }) {
  return (
    <div className="panel rounded-2xl p-5">
      <h2 className="eyebrow mb-4">{title}</h2>
      {children}
    </div>
  );
}

export default function AnalyticsPage() {
  const { data: reviews = [], isLoading } = useReviews();
  useLiveFeed();

  const m = useMemo(() => {
    const done = reviews.filter((r) => r.status === "completed");
    const allFindings: Finding[] = done.flatMap((r) => r.findings);
    const trend = [...done].reverse().map((r) => r.risk_score);
    const gated = done.filter((r) => r.gated).length;
    const blockRate = done.length ? Math.round((gated / done.length) * 100) : 0;

    const byCategory = countBy(allFindings, findingCategory);
    const byCwe = countBy(allFindings.filter((f) => f.cwe_id), (f) => f.cwe_id);
    const byRepo = countBy(done.flatMap((r) => r.findings.map(() => r.repo)), (x) => x);
    const toList = (rec: Record<string, number>, n = 8) =>
      Object.entries(rec).map(([label, value]) => ({ label, value })).sort((a, b) => b.value - a.value).slice(0, n);

    return {
      done, allFindings, trend, blockRate, gated,
      sev: severityCounts(done),
      categories: toList(byCategory),
      cwes: toList(byCwe),
      repos: toList(byRepo),
    };
  }, [reviews]);

  if (isLoading) {
    return <><PageHeader eyebrow="Insights" title="Analytics" /><div className="grid gap-4 sm:grid-cols-2">{[0,1,2,3].map(i => <div key={i} className="skeleton h-56 rounded-2xl" />)}</div></>;
  }

  return (
    <>
      <PageHeader eyebrow="Insights" title="Analytics & trends" />

      {/* KPI row */}
      <div className="mb-5 grid grid-cols-2 gap-4 sm:grid-cols-4">
        {[
          { label: "Reviews", value: m.done.length },
          { label: "Findings", value: m.allFindings.length },
          { label: "Blocked", value: m.gated, tone: "text-sev-critical" },
          { label: "Block rate", value: `${m.blockRate}%`, tone: "text-warn" },
        ].map((k) => (
          <div key={k.label} className="panel rounded-2xl p-4">
            <div className="eyebrow !text-[10px]">{k.label}</div>
            <div className={`mt-1.5 font-mono text-3xl font-bold tnum ${k.tone ?? "text-white"}`}>{k.value}</div>
          </div>
        ))}
      </div>

      <div className="grid gap-4 lg:grid-cols-2">
        <Panel title="Risk trend (oldest → newest)">
          {m.trend.length > 1
            ? <div className="flex justify-center py-4"><Sparkline values={m.trend} w={520} h={120} /></div>
            : <p className="py-8 text-center text-xs text-slate-600">Need at least two reviews to chart a trend.</p>}
        </Panel>
        <Panel title="Threat distribution">
          <div className="py-3"><SeverityBar counts={m.sev} /></div>
        </Panel>
        <Panel title="Findings by category"><BarList items={m.categories} /></Panel>
        <Panel title="Top CWEs"><BarList items={m.cwes} color="#ff8a3d" /></Panel>
        <Panel title="Most-flagged repositories"><BarList items={m.repos} color="#3ee0a3" empty="No findings yet" /></Panel>
        <Panel title="Guardrail effectiveness">
          <div className="flex items-center justify-around py-4 text-center">
            <div>
              <div className="font-mono text-3xl font-bold tnum text-safe">{m.allFindings.length}</div>
              <div className="mt-1 text-[11px] text-slate-500">findings surfaced<br />before merge</div>
            </div>
            <div className="h-12 w-px bg-border" />
            <div>
              <div className="font-mono text-3xl font-bold tnum text-sev-critical">{m.gated}</div>
              <div className="mt-1 text-[11px] text-slate-500">risky merges<br />blocked</div>
            </div>
          </div>
        </Panel>
      </div>
    </>
  );
}

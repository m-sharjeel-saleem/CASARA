"use client";

import { GitPullRequest, ShieldBan, Bug, Radar } from "lucide-react";

import type { Review, Stats } from "@/lib/types";
import { severityCounts } from "@/lib/utils";
import { RiskGauge, Sparkline, SeverityBar } from "./charts";

function Tile({ children, className = "" }: { children: React.ReactNode; className?: string }) {
  return <div className={`panel rounded-2xl p-5 shadow-tile ${className}`}>{children}</div>;
}

function Label({ icon, children }: { icon: React.ReactNode; children: React.ReactNode }) {
  return (
    <div className="flex items-center gap-2 text-slate-500">
      {icon}
      <span className="eyebrow !text-[10px]">{children}</span>
    </div>
  );
}

export function MetricsPanel({ stats, reviews }: { stats: Stats | null; reviews: Review[] }) {
  const counts = severityCounts(reviews);
  // Risk trend = risk scores oldest→newest from completed reviews (reviews arrive newest-first).
  const trend = [...reviews].reverse().filter((r) => r.status === "completed").map((r) => r.risk_score);
  const blockedPct = stats && stats.total_reviews > 0
    ? Math.round((stats.gated_count / stats.total_reviews) * 100) : 0;

  return (
    <div className="grid grid-cols-1 gap-4 lg:grid-cols-12">
      {/* Featured: average risk gauge */}
      <Tile className="lg:col-span-3">
        <Label icon={<Radar className="h-3.5 w-3.5" />}>Avg risk</Label>
        <div className="mt-3 flex items-center justify-center">
          <RiskGauge score={stats?.avg_risk ?? 0} size={104} />
        </div>
      </Tile>

      {/* Reviews + risk trend sparkline */}
      <Tile className="lg:col-span-4">
        <Label icon={<GitPullRequest className="h-3.5 w-3.5" />}>Reviews</Label>
        <div className="mt-2 flex items-end justify-between gap-3">
          <div className="font-mono text-4xl font-bold tnum text-white">
            {stats?.total_reviews ?? "—"}
          </div>
          <Sparkline values={trend} w={140} h={40} />
        </div>
        <div className="mt-1 text-[11px] text-slate-500">Composite risk per pull request</div>
      </Tile>

      {/* Blocked */}
      <Tile className="lg:col-span-2">
        <Label icon={<ShieldBan className="h-3.5 w-3.5" />}>Blocked</Label>
        <div className="mt-2 font-mono text-4xl font-bold tnum text-sev-critical">
          {stats?.gated_count ?? "—"}
        </div>
        <div className="mt-1 text-[11px] text-slate-500">{blockedPct}% of reviews gated</div>
      </Tile>

      {/* Findings */}
      <Tile className="lg:col-span-3">
        <Label icon={<Bug className="h-3.5 w-3.5" />}>Findings</Label>
        <div className="mt-2 font-mono text-4xl font-bold tnum text-white">
          {stats?.total_findings ?? "—"}
        </div>
        <div className="mt-1 text-[11px] text-slate-500">Across all reviews</div>
      </Tile>

      {/* Threat distribution */}
      <Tile className="lg:col-span-12">
        <Label icon={<Radar className="h-3.5 w-3.5" />}>Threat distribution</Label>
        <div className="mt-4">
          <SeverityBar counts={counts} />
        </div>
      </Tile>
    </div>
  );
}

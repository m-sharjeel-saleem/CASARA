import { Activity, FileWarning, ShieldAlert, ShieldCheck } from "lucide-react";

import type { Stats } from "@/lib/types";

function Stat({ icon, label, value, tone = "" }: {
  icon: React.ReactNode; label: string; value: string | number; tone?: string;
}) {
  return (
    <div className="glass rounded-2xl p-4">
      <div className="flex items-center gap-1.5 text-[11px] uppercase tracking-wide text-zinc-500">
        {icon} {label}
      </div>
      <div className={`mt-1 font-mono text-2xl font-semibold ${tone || "text-white"}`}>{value}</div>
    </div>
  );
}

export function StatsBar({ stats }: { stats: Stats | null }) {
  return (
    <div className="grid grid-cols-2 gap-3 sm:grid-cols-4">
      <Stat icon={<Activity className="h-3 w-3" />} label="Reviews" value={stats?.total_reviews ?? "—"} />
      <Stat icon={<ShieldAlert className="h-3 w-3" />} label="Blocked" value={stats?.gated_count ?? "—"} tone="text-danger" />
      <Stat icon={<ShieldCheck className="h-3 w-3" />} label="Avg risk" value={stats ? `${stats.avg_risk}/10` : "—"} tone="text-warn" />
      <Stat icon={<FileWarning className="h-3 w-3" />} label="Findings" value={stats?.total_findings ?? "—"} />
    </div>
  );
}

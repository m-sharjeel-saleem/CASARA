"use client";

import type { Severity } from "@/lib/types";
import { riskHex, SEV_HEX, SEV_ORDER } from "@/lib/utils";

/** Circular risk gauge (0–10) with a coloured arc and centred value. */
export function RiskGauge({ score, size = 96 }: { score: number; size?: number }) {
  const r = (size - 12) / 2;
  const c = 2 * Math.PI * r;
  const pct = Math.max(0, Math.min(1, score / 10));
  const hex = riskHex(score);
  return (
    <div className="relative grid place-items-center" style={{ width: size, height: size }}>
      <svg width={size} height={size} className="-rotate-90">
        <circle cx={size / 2} cy={size / 2} r={r} fill="none" stroke="rgba(148,163,184,0.14)" strokeWidth={6} />
        <circle
          cx={size / 2} cy={size / 2} r={r} fill="none" stroke={hex} strokeWidth={6}
          strokeLinecap="round" strokeDasharray={c}
          style={{ strokeDashoffset: c * (1 - pct), filter: `drop-shadow(0 0 6px ${hex}66)`,
                   transition: "stroke-dashoffset 0.9s cubic-bezier(0.22,1,0.36,1)" }}
        />
      </svg>
      <div className="absolute text-center leading-none">
        <div className="font-mono text-xl font-bold tnum" style={{ color: hex }}>{score.toFixed(1)}</div>
        <div className="mt-0.5 text-[9px] uppercase tracking-wider text-slate-500">/10</div>
      </div>
    </div>
  );
}

/** Sparkline of recent risk scores (oldest→newest), endpoint emphasised. */
export function Sparkline({ values, w = 120, h = 34 }: { values: number[]; w?: number; h?: number }) {
  if (values.length < 2) return <div style={{ width: w, height: h }} />;
  const max = 10, min = 0;
  const step = w / (values.length - 1);
  const pts = values.map((v, i) => [i * step, h - ((v - min) / (max - min)) * (h - 4) - 2]);
  const line = pts.map((p, i) => `${i ? "L" : "M"}${p[0].toFixed(1)},${p[1].toFixed(1)}`).join(" ");
  const area = `${line} L${w},${h} L0,${h} Z`;
  const last = pts[pts.length - 1];
  return (
    <svg width={w} height={h} className="overflow-visible">
      <defs>
        <linearGradient id="spark" x1="0" y1="0" x2="0" y2="1">
          <stop offset="0%" stopColor="#6d7bff" stopOpacity="0.35" />
          <stop offset="100%" stopColor="#6d7bff" stopOpacity="0" />
        </linearGradient>
      </defs>
      <path d={area} fill="url(#spark)" />
      <path d={line} fill="none" stroke="#a5b0ff" strokeWidth={1.5} strokeLinecap="round" strokeLinejoin="round" />
      <circle cx={last[0]} cy={last[1]} r={2.6} fill="#fff" stroke="#6d7bff" strokeWidth={1.5} />
    </svg>
  );
}

/** Ranked horizontal bar list (category/repo/CWE breakdowns). */
export function BarList({ items, color = "#6d7bff", empty = "No data yet" }: {
  items: { label: string; value: number; href?: string }[]; color?: string; empty?: string;
}) {
  if (items.length === 0) return <p className="py-6 text-center text-xs text-slate-600">{empty}</p>;
  const max = Math.max(...items.map((i) => i.value), 1);
  return (
    <div className="space-y-2">
      {items.map((it) => (
        <div key={it.label} className="group">
          <div className="mb-1 flex items-center justify-between text-[12px]">
            <span className="truncate pr-2 text-slate-300">{it.label}</span>
            <span className="font-mono tnum text-slate-400">{it.value}</span>
          </div>
          <div className="h-1.5 w-full overflow-hidden rounded-full bg-white/5">
            <div className="h-full rounded-full transition-all"
              style={{ width: `${(it.value / max) * 100}%`, background: color }} />
          </div>
        </div>
      ))}
    </div>
  );
}

/** Stacked horizontal bar of severity counts with a legend. */
export function SeverityBar({ counts }: { counts: Record<Severity, number> }) {
  const total = SEV_ORDER.reduce((s, k) => s + counts[k], 0);
  return (
    <div>
      <div className="flex h-2.5 w-full overflow-hidden rounded-full bg-white/5">
        {total === 0 ? (
          <div className="h-full w-full bg-white/5" />
        ) : (
          SEV_ORDER.map((s) =>
            counts[s] > 0 ? (
              <div key={s} title={`${s}: ${counts[s]}`}
                style={{ width: `${(counts[s] / total) * 100}%`, background: SEV_HEX[s] }} />
            ) : null,
          )
        )}
      </div>
      <div className="mt-3 flex flex-wrap gap-x-4 gap-y-1.5">
        {SEV_ORDER.map((s) => (
          <span key={s} className="inline-flex items-center gap-1.5 text-[11px] text-slate-400">
            <span className="h-2 w-2 rounded-sm" style={{ background: SEV_HEX[s] }} />
            <span className="capitalize">{s}</span>
            <span className="font-mono tnum text-slate-300">{counts[s]}</span>
          </span>
        ))}
      </div>
    </div>
  );
}

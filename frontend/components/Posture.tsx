"use client";

import { motion } from "framer-motion";
import { ShieldCheck, AlertTriangle, Bug, GitPullRequest } from "lucide-react";

import type { Review, Severity } from "@/lib/types";
import { gradeHex, isAudit, SEV_HEX, SEV_ORDER, severityCounts } from "@/lib/utils";

/** Large animated A–F security-grade ring — the signature posture widget. */
export function GradeRing({ grade, score, size = 168 }: { grade: string; score: number; size?: number }) {
  const stroke = 12;
  const r = (size - stroke) / 2;
  const c = 2 * Math.PI * r;
  const pct = Math.max(0.04, 1 - score / 10); // higher fill = safer
  const hex = gradeHex(grade);
  return (
    <div className="relative grid shrink-0 place-items-center" style={{ width: size, height: size }}>
      <svg width={size} height={size} className="-rotate-90">
        <circle cx={size / 2} cy={size / 2} r={r} fill="none" stroke="rgba(148,163,184,0.12)" strokeWidth={stroke} />
        <motion.circle
          cx={size / 2} cy={size / 2} r={r} fill="none" stroke={hex} strokeWidth={stroke}
          strokeLinecap="round" strokeDasharray={c}
          initial={{ strokeDashoffset: c }} animate={{ strokeDashoffset: c * (1 - pct) }}
          transition={{ duration: 1.1, ease: [0.22, 1, 0.36, 1] }}
          style={{ filter: `drop-shadow(0 0 10px ${hex}66)` }}
        />
      </svg>
      <div className="absolute text-center leading-none">
        <div className="font-display font-extrabold" style={{ fontSize: size * 0.34, color: hex }}>{grade}</div>
        <div className="mt-1 text-[10px] uppercase tracking-[0.2em] text-slate-500">grade</div>
      </div>
    </div>
  );
}

function MiniStat({ icon, label, value, tone }: {
  icon: React.ReactNode; label: string; value: number | string; tone?: string;
}) {
  return (
    <div className="flex items-center gap-3 rounded-xl border border-border bg-white/[0.02] px-4 py-3">
      <span className="text-slate-500">{icon}</span>
      <div>
        <div className={`font-mono text-xl font-bold tnum leading-none ${tone ?? "text-white"}`}>{value}</div>
        <div className="mt-1 text-[10px] uppercase tracking-wider text-slate-500">{label}</div>
      </div>
    </div>
  );
}

const VERDICT: Record<string, string> = {
  A: "Excellent posture — minimal risk across reviewed code.",
  B: "Solid posture with a few items worth addressing.",
  C: "Moderate risk — several findings need attention.",
  D: "Elevated risk — prioritise remediation soon.",
  F: "Critical risk — immediate remediation required.",
};

/** The hero banner: grade ring + verdict + key metrics + severity strip. */
export function PostureHero({ reviews }: { reviews: Review[] }) {
  const done = reviews.filter((r) => r.status === "completed");
  const findings = done.flatMap((r) => r.findings);
  const counts = severityCounts(done);
  const total = SEV_ORDER.reduce((s, k) => s + counts[k], 0);
  const critical = counts.critical + counts.high;
  const blocked = done.filter((r) => !isAudit(r.pr_number) && r.gated).length;
  const prReviews = done.filter((r) => !isAudit(r.pr_number)).length;
  const avg = done.length ? done.reduce((s, r) => s + r.risk_score, 0) / done.length : 0;
  const grade = avg < 2 ? "A" : avg < 4 ? "B" : avg < 6 ? "C" : avg < 8 ? "D" : "F";
  const hex = gradeHex(grade);

  return (
    <motion.div
      initial={{ opacity: 0, y: 12 }} animate={{ opacity: 1, y: 0 }} transition={{ duration: 0.5 }}
      className="relative overflow-hidden rounded-3xl border border-border p-6 sm:p-8"
      style={{ background: `radial-gradient(120% 140% at 0% 0%, ${hex}1a, transparent 55%), linear-gradient(180deg, rgba(255,255,255,0.04), rgba(255,255,255,0.012)), #0e1320` }}
    >
      <div className="radar-sweep pointer-events-none absolute -right-24 -top-24 -z-0 h-72 w-72 overflow-hidden rounded-full opacity-20" />
      <div className="relative flex flex-col items-center gap-7 lg:flex-row lg:items-center">
        <div className="flex items-center gap-5">
          <GradeRing grade={grade} score={avg} />
          <div className="lg:hidden">
            <div className="eyebrow mb-1">Security posture</div>
            <p className="max-w-xs text-sm text-slate-300">{VERDICT[grade]}</p>
          </div>
        </div>

        <div className="min-w-0 flex-1">
          <div className="mb-1 hidden lg:block">
            <div className="eyebrow mb-1.5">Security posture</div>
            <h2 className="font-display text-2xl font-bold tracking-tight text-white">
              Your code is <span style={{ color: hex }}>grade {grade}</span>
            </h2>
            <p className="mt-1.5 max-w-md text-sm text-slate-400">{VERDICT[grade]}</p>
          </div>

          <div className="mt-4 grid grid-cols-2 gap-3 sm:grid-cols-4">
            <MiniStat icon={<Bug className="h-4 w-4" />} label="Findings" value={findings.length} />
            <MiniStat icon={<AlertTriangle className="h-4 w-4" />} label="Crit+High" value={critical} tone="text-sev-critical" />
            <MiniStat icon={<GitPullRequest className="h-4 w-4" />} label="PR reviews" value={prReviews} />
            <MiniStat icon={<ShieldCheck className="h-4 w-4" />} label="Blocked" value={blocked} tone="text-warn" />
          </div>

          {total > 0 && (
            <div className="mt-4">
              <div className="flex h-2 w-full overflow-hidden rounded-full bg-white/5">
                {SEV_ORDER.map((s) => counts[s] > 0 && (
                  <div key={s} title={`${s}: ${counts[s]}`} style={{ width: `${(counts[s] / total) * 100}%`, background: SEV_HEX[s as Severity] }} />
                ))}
              </div>
              <div className="mt-2 flex flex-wrap gap-x-4 gap-y-1">
                {SEV_ORDER.map((s) => counts[s] > 0 && (
                  <span key={s} className="inline-flex items-center gap-1.5 text-[11px] text-slate-400">
                    <span className="h-2 w-2 rounded-sm" style={{ background: SEV_HEX[s as Severity] }} />
                    <span className="capitalize">{s}</span><span className="font-mono tnum text-slate-300">{counts[s]}</span>
                  </span>
                ))}
              </div>
            </div>
          )}
        </div>
      </div>
    </motion.div>
  );
}

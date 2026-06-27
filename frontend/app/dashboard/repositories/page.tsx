"use client";

import { FolderGit2, Loader2, Radar, ShieldAlert } from "lucide-react";
import { useMemo, useState } from "react";

import { InstallButton } from "@/components/InstallButton";
import { PageHeader } from "@/components/PageHeader";
import { api } from "@/lib/api";
import { useInstallations, useLiveFeed, useReviews } from "@/lib/hooks";
import { gradeForRisk, gradeHex, isAudit, riskColor, timeAgo } from "@/lib/utils";

export default function RepositoriesPage() {
  const { data: reviews = [], mutate } = useReviews();
  const { data: installations = [] } = useInstallations();
  useLiveFeed();
  const [auditRepo, setAuditRepo] = useState("");
  const [busy, setBusy] = useState<string | null>(null);
  const [msg, setMsg] = useState<string | null>(null);

  const runAudit = async (repo: string) => {
    if (!repo.trim()) return;
    setBusy(repo); setMsg(null);
    try {
      await api.runAudit(repo.trim());
      setMsg(`Audit started for ${repo.trim()} — results appear in the feed shortly.`);
      setAuditRepo("");
      setTimeout(() => mutate(), 2000);
    } catch (e) {
      setMsg(e instanceof Error ? e.message : "Audit failed to start");
    } finally {
      setBusy(null);
    }
  };

  const repos = useMemo(() => {
    const map = new Map<string, { repo: string; reviews: number; findings: number; blocked: number; avg: number; last: string; grade: string | null }>();
    for (const r of reviews) {
      const e = map.get(r.repo) ?? { repo: r.repo, reviews: 0, findings: 0, blocked: 0, avg: 0, last: r.created_at, grade: null };
      if (isAudit(r.pr_number)) {
        if (r.status === "completed") e.grade = gradeForRisk(r.risk_score);
      } else {
        e.reviews += 1; e.avg += r.risk_score; e.blocked += r.gated ? 1 : 0;
      }
      e.findings += r.findings.length;
      if (new Date(r.created_at) > new Date(e.last)) e.last = r.created_at;
      map.set(r.repo, e);
    }
    return [...map.values()].map((e) => ({ ...e, avg: e.reviews ? +(e.avg / e.reviews).toFixed(1) : 0 }))
      .sort((a, b) => b.findings - a.findings);
  }, [reviews]);

  return (
    <>
      <PageHeader eyebrow="Connected" title="Repositories">
        <InstallButton size="sm" />
      </PageHeader>

      {installations.length > 0 && (
        <div className="mb-5 flex flex-wrap gap-2">
          {installations.map((i) => (
            <span key={i.id} className="inline-flex items-center gap-2 rounded-full border border-safe/25 bg-safe/[0.05] px-3 py-1.5 text-xs text-slate-300">
              <FolderGit2 className="h-3.5 w-3.5 text-safe" /> {i.account}
              <span className="text-slate-600">· connected {timeAgo(i.created_at)}</span>
            </span>
          ))}
        </div>
      )}

      {/* Whole-repo audit trigger */}
      <div className="panel mb-5 rounded-2xl p-4">
        <div className="mb-2 flex items-center gap-2">
          <Radar className="h-4 w-4 text-accent-soft" />
          <h2 className="eyebrow">Run a full security audit</h2>
        </div>
        <p className="mb-3 text-[12px] text-slate-500">
          Scans the entire repository (not just a PR) with the full suite — vulns, secrets, misconfig,
          and <span className="text-accent-soft">malicious dependencies</span> — and assigns a security grade.
        </p>
        <div className="flex flex-col gap-2 sm:flex-row">
          <input value={auditRepo} onChange={(e) => setAuditRepo(e.target.value)} placeholder="owner/repo"
            className="h-10 flex-1 rounded-lg border border-border bg-black/30 px-3 font-mono text-sm text-slate-100 placeholder:text-slate-600 focus:outline-none focus:ring-2 focus:ring-accent/40" />
          <button onClick={() => runAudit(auditRepo)} disabled={busy === auditRepo}
            className="inline-flex h-10 items-center justify-center gap-2 rounded-lg bg-accent px-5 text-sm font-semibold text-white shadow-glow transition hover:bg-accent-deep disabled:opacity-50">
            {busy === auditRepo ? <Loader2 className="h-4 w-4 animate-spin" /> : <Radar className="h-4 w-4" />} Run audit
          </button>
        </div>
        {msg && <p className="mt-2 text-xs text-accent-soft">{msg}</p>}
      </div>

      {repos.length === 0 ? (
        <div className="panel rounded-2xl py-16 text-center">
          <FolderGit2 className="mx-auto h-8 w-8 text-slate-600" />
          <p className="mt-3 text-sm text-slate-400">No repository activity yet.</p>
          <p className="mt-1 text-xs text-slate-600">Install CASARA on a repo and open a PR, or run an audit above.</p>
        </div>
      ) : (
        <div className="overflow-x-auto">
          <table className="w-full min-w-[720px] border-separate border-spacing-y-2">
            <thead>
              <tr className="text-left text-[11px] uppercase tracking-wider text-slate-500">
                <th className="px-4 py-2 font-medium">Repository</th>
                <th className="px-4 py-2 font-medium">Grade</th>
                <th className="px-4 py-2 font-medium tnum">Reviews</th>
                <th className="px-4 py-2 font-medium tnum">Findings</th>
                <th className="px-4 py-2 font-medium tnum">Blocked</th>
                <th className="px-4 py-2 font-medium tnum">Avg risk</th>
                <th className="px-4 py-2 font-medium">Last</th>
                <th className="px-4 py-2 font-medium"></th>
              </tr>
            </thead>
            <tbody>
              {repos.map((r) => (
                <tr key={r.repo} className="panel rounded-xl text-sm">
                  <td className="rounded-l-xl px-4 py-3 font-mono text-slate-200">{r.repo}</td>
                  <td className="px-4 py-3">
                    {r.grade
                      ? <span className="grid h-7 w-7 place-items-center rounded-lg border font-display text-sm font-bold"
                          style={{ color: gradeHex(r.grade), borderColor: `${gradeHex(r.grade)}55`, background: `${gradeHex(r.grade)}14` }}>{r.grade}</span>
                      : <span className="text-[11px] text-slate-600">—</span>}
                  </td>
                  <td className="px-4 py-3 tnum text-slate-300">{r.reviews}</td>
                  <td className="px-4 py-3 tnum text-slate-300">{r.findings}</td>
                  <td className="px-4 py-3 tnum">{r.blocked > 0 ? <span className="inline-flex items-center gap-1 text-sev-critical"><ShieldAlert className="h-3.5 w-3.5" />{r.blocked}</span> : <span className="text-slate-500">0</span>}</td>
                  <td className={`px-4 py-3 font-mono tnum font-semibold ${riskColor(r.avg)}`}>{r.avg}</td>
                  <td className="px-4 py-3 text-slate-500">{timeAgo(r.last)}</td>
                  <td className="rounded-r-xl px-4 py-3 text-right">
                    <button onClick={() => runAudit(r.repo)} disabled={busy === r.repo}
                      className="inline-flex items-center gap-1 rounded-lg border border-border px-2.5 py-1 text-[11px] text-slate-300 transition hover:bg-white/5 disabled:opacity-50">
                      {busy === r.repo ? <Loader2 className="h-3 w-3 animate-spin" /> : <Radar className="h-3 w-3" />} Audit
                    </button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </>
  );
}

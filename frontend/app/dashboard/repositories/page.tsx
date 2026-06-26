"use client";

import { FolderGit2, ShieldAlert } from "lucide-react";
import { useMemo } from "react";

import { InstallButton } from "@/components/InstallButton";
import { PageHeader } from "@/components/PageHeader";
import { useInstallations, useLiveFeed, useReviews } from "@/lib/hooks";
import { riskColor, timeAgo } from "@/lib/utils";

export default function RepositoriesPage() {
  const { data: reviews = [] } = useReviews();
  const { data: installations = [] } = useInstallations();
  useLiveFeed();

  const repos = useMemo(() => {
    const map = new Map<string, { repo: string; reviews: number; findings: number; blocked: number; avg: number; last: string }>();
    for (const r of reviews) {
      const e = map.get(r.repo) ?? { repo: r.repo, reviews: 0, findings: 0, blocked: 0, avg: 0, last: r.created_at };
      e.reviews += 1; e.findings += r.findings.length; e.blocked += r.gated ? 1 : 0;
      e.avg += r.risk_score;
      if (new Date(r.created_at) > new Date(e.last)) e.last = r.created_at;
      map.set(r.repo, e);
    }
    return [...map.values()].map((e) => ({ ...e, avg: e.reviews ? +(e.avg / e.reviews).toFixed(1) : 0 }))
      .sort((a, b) => b.reviews - a.reviews);
  }, [reviews]);

  return (
    <>
      <PageHeader eyebrow="Connected" title="Repositories">
        <InstallButton size="sm" />
      </PageHeader>

      {installations.length > 0 && (
        <div className="mb-5 flex flex-wrap gap-2">
          {installations.map((i) => (
            <span key={i.id} className="inline-flex items-center gap-2 rounded-full border border-border bg-white/[0.02] px-3 py-1.5 text-xs text-slate-300">
              <FolderGit2 className="h-3.5 w-3.5 text-accent-soft" /> {i.account}
              <span className="text-slate-600">· {i.account_type || "account"}</span>
            </span>
          ))}
        </div>
      )}

      {repos.length === 0 ? (
        <div className="panel rounded-2xl py-16 text-center">
          <FolderGit2 className="mx-auto h-8 w-8 text-slate-600" />
          <p className="mt-3 text-sm text-slate-400">No repository activity yet.</p>
          <p className="mt-1 text-xs text-slate-600">Install CASARA on a repo and open a pull request.</p>
        </div>
      ) : (
        <div className="overflow-x-auto">
          <table className="w-full min-w-[640px] border-separate border-spacing-y-2">
            <thead>
              <tr className="text-left text-[11px] uppercase tracking-wider text-slate-500">
                <th className="px-4 py-2 font-medium">Repository</th>
                <th className="px-4 py-2 font-medium tnum">Reviews</th>
                <th className="px-4 py-2 font-medium tnum">Findings</th>
                <th className="px-4 py-2 font-medium tnum">Blocked</th>
                <th className="px-4 py-2 font-medium tnum">Avg risk</th>
                <th className="px-4 py-2 font-medium">Last activity</th>
              </tr>
            </thead>
            <tbody>
              {repos.map((r) => (
                <tr key={r.repo} className="panel rounded-xl text-sm">
                  <td className="rounded-l-xl px-4 py-3 font-mono text-slate-200">{r.repo}</td>
                  <td className="px-4 py-3 tnum text-slate-300">{r.reviews}</td>
                  <td className="px-4 py-3 tnum text-slate-300">{r.findings}</td>
                  <td className="px-4 py-3 tnum">
                    {r.blocked > 0
                      ? <span className="inline-flex items-center gap-1 text-sev-critical"><ShieldAlert className="h-3.5 w-3.5" />{r.blocked}</span>
                      : <span className="text-slate-500">0</span>}
                  </td>
                  <td className={`px-4 py-3 font-mono tnum font-semibold ${riskColor(r.avg)}`}>{r.avg}</td>
                  <td className="rounded-r-xl px-4 py-3 text-slate-500">{timeAgo(r.last)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </>
  );
}

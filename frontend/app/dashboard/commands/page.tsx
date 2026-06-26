"use client";

import { MessageSquare, Terminal } from "lucide-react";

import { PageHeader } from "@/components/PageHeader";

const COMMANDS = [
  { cmd: "@casara review", desc: "Run a fresh security review on this pull request." },
  { cmd: "/casara review", desc: "Alias for @casara review (slash syntax)." },
];

const CONFIG_KEYS = [
  { k: "languages", v: "Scope analysis to specific languages (empty = all)." },
  { k: "gate.level", v: "off · warning · error — whether findings block the merge." },
  { k: "gate.threshold", v: "Composite risk (0–10) at/above which a PR is gated." },
  { k: "noise.min_confidence", v: "Drop AI findings below LOW / MEDIUM / HIGH confidence." },
  { k: "noise.max_comments", v: "Cap findings shown per PR (rest live on the dashboard)." },
  { k: "rules", v: "Plain-English rules scoped to a path glob — enforced by the AI." },
  { k: "severity_overrides", v: "Force a minimum severity for specific CWEs (raise-only)." },
  { k: "semgrep_config", v: "Add a custom Semgrep ruleset (registry pack or repo path)." },
];

export default function CommandsPage() {
  return (
    <>
      <PageHeader eyebrow="Reference" title="Commands & configuration" />

      <section className="panel mb-5 rounded-2xl p-5">
        <div className="mb-3 flex items-center gap-2">
          <MessageSquare className="h-4 w-4 text-accent-soft" />
          <h2 className="eyebrow">PR chat commands</h2>
        </div>
        <p className="mb-4 text-[13px] text-slate-400">
          Comment any of these on a pull request to trigger CASARA on demand — no dashboard needed.
        </p>
        <div className="space-y-2">
          {COMMANDS.map((c) => (
            <div key={c.cmd} className="flex flex-col gap-1 rounded-lg border border-border bg-black/20 p-3 sm:flex-row sm:items-center">
              <code className="w-fit rounded bg-accent/10 px-2 py-1 font-mono text-[13px] text-accent-soft">{c.cmd}</code>
              <span className="text-[13px] text-slate-400 sm:ml-4">{c.desc}</span>
            </div>
          ))}
        </div>
      </section>

      <section className="panel mb-5 rounded-2xl p-5">
        <div className="mb-3 flex items-center gap-2">
          <Terminal className="h-4 w-4 text-accent-soft" />
          <h2 className="eyebrow">Automatic reviews</h2>
        </div>
        <p className="text-[13px] leading-relaxed text-slate-400">
          Once CASARA is installed on a repo, every pull request is reviewed <strong className="text-slate-200">automatically</strong> on
          open, reopen, and new commits. You don&apos;t need to visit this site — the review and a
          pass/block status check appear right on the PR. This dashboard is for monitoring and configuration.
        </p>
      </section>

      <section className="panel rounded-2xl p-5">
        <h2 className="eyebrow mb-3">Configuration keys (.casara.yml)</h2>
        <p className="mb-4 text-[13px] text-slate-400">
          Set these in <a href="/dashboard/settings" className="text-accent-soft hover:text-white">Settings &amp; Rules</a> (org-wide),
          or commit a <code className="text-accent-soft">.casara.yml</code> to a repo to override per-repo.
        </p>
        <div className="overflow-x-auto">
          <table className="w-full min-w-[520px] text-sm">
            <tbody>
              {CONFIG_KEYS.map((c) => (
                <tr key={c.k} className="border-b border-border/60">
                  <td className="py-2.5 pr-4 align-top font-mono text-[12px] text-accent-soft">{c.k}</td>
                  <td className="py-2.5 text-[13px] text-slate-400">{c.v}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </section>
    </>
  );
}

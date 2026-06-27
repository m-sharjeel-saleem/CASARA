"use client";

import { CheckCircle2, Github, PlugZap } from "lucide-react";

import { InstallButton } from "./InstallButton";
import { useInstallations } from "@/lib/hooks";
import { timeAgo } from "@/lib/utils";

/** Prominent "is a GitHub account connected?" strip. Answers the #1 onboarding question. */
export function ConnectionStatus() {
  const { data: installations = [], isLoading } = useInstallations();

  if (isLoading) return <div className="skeleton mb-5 h-16 rounded-2xl" />;

  if (installations.length === 0) {
    return (
      <div className="mb-5 flex flex-col items-start gap-3 rounded-2xl border border-warn/25 bg-warn/[0.06] p-4 sm:flex-row sm:items-center sm:justify-between">
        <div className="flex items-center gap-3">
          <span className="grid h-9 w-9 place-items-center rounded-xl border border-warn/30 bg-warn/10 text-warn">
            <PlugZap className="h-5 w-5" />
          </span>
          <div>
            <div className="text-sm font-semibold text-slate-100">No GitHub account connected</div>
            <div className="text-[12px] text-slate-400">Install the CASARA app to start reviewing pull requests automatically.</div>
          </div>
        </div>
        <InstallButton size="sm" />
      </div>
    );
  }

  return (
    <div className="mb-5 flex flex-col gap-3 rounded-2xl border border-safe/20 bg-safe/[0.05] p-4 sm:flex-row sm:items-center sm:justify-between">
      <div className="flex items-center gap-3">
        <span className="grid h-9 w-9 place-items-center rounded-xl border border-safe/30 bg-safe/10 text-safe">
          <CheckCircle2 className="h-5 w-5" />
        </span>
        <div>
          <div className="flex items-center gap-1.5 text-sm font-semibold text-slate-100">
            <Github className="h-3.5 w-3.5 text-slate-400" />
            Connected · {installations.length} account{installations.length > 1 ? "s" : ""}
          </div>
          <div className="flex flex-wrap items-center gap-x-2 gap-y-0.5 text-[12px] text-slate-400">
            {installations.slice(0, 4).map((i) => (
              <span key={i.id} className="font-mono text-slate-300">{i.account}</span>
            ))}
            <span className="text-slate-600">· connected {timeAgo(installations[0].created_at)}</span>
          </div>
        </div>
      </div>
      <InstallButton size="sm" />
    </div>
  );
}

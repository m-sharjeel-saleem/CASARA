"use client";

import { Github } from "lucide-react";

import { InstallButton } from "./InstallButton";
import { useLiveStatus } from "@/lib/hooks";

export function AppTopbar() {
  const live = useLiveStatus();
  return (
    <header className="flex h-16 items-center justify-between gap-3 border-b border-border px-5">
      <div className="lg:hidden flex items-center gap-2">
        {/* eslint-disable-next-line @next/next/no-img-element */}
        <img src="/logo.svg" alt="" className="h-6 w-6" />
        <span className="font-display text-sm font-bold text-white">CASARA</span>
      </div>
      <div className="ml-auto flex items-center gap-3">
        <span className="inline-flex items-center gap-2 rounded-full border border-border bg-white/[0.02] px-3 py-1.5 text-xs text-slate-400">
          <span className="relative flex h-1.5 w-1.5">
            {live && <span className="absolute inline-flex h-full w-full animate-ping rounded-full bg-safe opacity-60" />}
            <span className={`relative inline-flex h-1.5 w-1.5 rounded-full ${live ? "bg-safe" : "bg-slate-600"}`} />
          </span>
          <span className="font-mono tracking-wide">{live ? "LIVE" : "OFFLINE"}</span>
        </span>
        <a href="https://github.com/m-sharjeel-saleem/CASARA" target="_blank" rel="noopener noreferrer"
          aria-label="Source on GitHub"
          className="rounded-lg border border-border p-2 text-slate-300 transition-colors hover:bg-white/5 hover:text-white">
          <Github className="h-4 w-4" />
        </a>
        <InstallButton size="sm" />
      </div>
    </header>
  );
}

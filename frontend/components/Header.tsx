import { Github } from "lucide-react";
import Link from "next/link";

import { InstallButton } from "./InstallButton";

export function Header({ live }: { live: boolean }) {
  return (
    <header className="sticky top-0 z-40 border-b border-border bg-bg/70 backdrop-blur-xl">
      <div className="mx-auto flex h-16 max-w-7xl items-center justify-between px-5">
        <Link href="/" className="flex items-center gap-3">
          {/* eslint-disable-next-line @next/next/no-img-element */}
          <img src="/logo.svg" alt="CASARA" className="h-8 w-8" />
          <div className="leading-tight">
            <div className="font-display text-[15px] font-bold tracking-tight text-white">CASARA</div>
            <div className="eyebrow !text-[9px] !tracking-[0.18em]">Security Console</div>
          </div>
        </Link>

        <div className="flex items-center gap-3">
          <span className="inline-flex items-center gap-2 rounded-full border border-border bg-white/[0.02] px-3 py-1.5 text-xs text-slate-400">
            <span className="relative flex h-1.5 w-1.5">
              {live && <span className="absolute inline-flex h-full w-full animate-ping rounded-full bg-safe opacity-60" />}
              <span className={`relative inline-flex h-1.5 w-1.5 rounded-full ${live ? "bg-safe" : "bg-slate-600"}`} />
            </span>
            <span className="font-mono tracking-wide">{live ? "LIVE" : "OFFLINE"}</span>
          </span>
          <a
            href="https://github.com/m-sharjeel-saleem/CASARA"
            target="_blank" rel="noopener noreferrer" aria-label="Source on GitHub"
            className="rounded-lg border border-border p-2 text-slate-300 transition-colors hover:bg-white/5 hover:text-white"
          >
            <Github className="h-4 w-4" />
          </a>
          <div className="hidden sm:block"><InstallButton size="sm" /></div>
        </div>
      </div>
    </header>
  );
}

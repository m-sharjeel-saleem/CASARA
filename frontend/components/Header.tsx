import { Github } from "lucide-react";

export function Header({ live }: { live: boolean }) {
  return (
    <header className="sticky top-0 z-40 border-b border-border bg-bg/70 backdrop-blur-xl">
      <div className="mx-auto flex h-16 max-w-7xl items-center justify-between px-5">
        <div className="flex items-center gap-3">
          {/* eslint-disable-next-line @next/next/no-img-element */}
          <img src="/logo.svg" alt="CASARA" className="h-9 w-9" />
          <div className="leading-tight">
            <div className="text-[15px] font-semibold tracking-tight text-white">CASARA</div>
            <div className="text-[11px] text-zinc-500">Automated PR Security Review</div>
          </div>
        </div>
        <div className="flex items-center gap-3">
          <span className="inline-flex items-center gap-1.5 rounded-full border border-border px-2.5 py-1 text-xs text-zinc-400">
            <span className={`h-1.5 w-1.5 rounded-full ${live ? "bg-safe animate-pulse" : "bg-zinc-600"}`} />
            {live ? "Live" : "Offline"}
          </span>
          <a
            href="https://github.com/m-sharjeel-saleem"
            target="_blank"
            rel="noopener noreferrer"
            aria-label="GitHub"
            className="rounded-lg border border-border p-2 text-zinc-300 transition-colors hover:bg-white/5 hover:text-white"
          >
            <Github className="h-4 w-4" />
          </a>
        </div>
      </div>
    </header>
  );
}

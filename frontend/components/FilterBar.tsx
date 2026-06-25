"use client";

import { Search } from "lucide-react";

export type ReviewFilter = "all" | "blocked" | "passed";

export function FilterBar({
  query, setQuery, filter, setFilter, counts,
}: {
  query: string; setQuery: (s: string) => void;
  filter: ReviewFilter; setFilter: (f: ReviewFilter) => void;
  counts: Record<ReviewFilter, number>;
}) {
  const tabs: { key: ReviewFilter; label: string }[] = [
    { key: "all", label: "All" },
    { key: "blocked", label: "Blocked" },
    { key: "passed", label: "Passed" },
  ];
  return (
    <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
      <div className="relative w-full sm:max-w-xs">
        <Search className="pointer-events-none absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-slate-500" />
        <input
          value={query}
          onChange={(e) => setQuery(e.target.value)}
          placeholder="Filter by repo or title…"
          className="h-9 w-full rounded-lg border border-border bg-black/30 pl-9 pr-3 text-sm text-slate-100 placeholder:text-slate-600 focus:outline-none focus:ring-2 focus:ring-accent/40"
        />
      </div>
      <div className="inline-flex rounded-lg border border-border bg-black/20 p-1">
        {tabs.map((t) => (
          <button
            key={t.key}
            onClick={() => setFilter(t.key)}
            className={`rounded-md px-3 py-1.5 text-xs font-medium transition-colors ${
              filter === t.key ? "bg-accent/15 text-accent-soft" : "text-slate-400 hover:text-slate-200"
            }`}
          >
            {t.label} <span className="ml-1 font-mono tnum text-slate-500">{counts[t.key]}</span>
          </button>
        ))}
      </div>
    </div>
  );
}

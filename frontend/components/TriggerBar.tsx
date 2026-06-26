"use client";

import { Loader2, Radar } from "lucide-react";
import { useState } from "react";

import { api } from "@/lib/api";

export function TriggerBar({ onTriggered }: { onTriggered: () => void }) {
  const [repo, setRepo] = useState("");
  const [pr, setPr] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [ok, setOk] = useState(false);

  const submit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!repo.trim()) return;
    const looksLikeUrl = /github\.com\/.+\/pull\/\d+/.test(repo);
    if (!looksLikeUrl && !pr.trim()) {
      setError("Enter a PR number, or paste the full PR URL into the first box.");
      return;
    }
    setBusy(true); setError(null); setOk(false);
    try {
      await api.triggerReview(repo.trim(), pr.trim() ? parseInt(pr, 10) : undefined);
      setOk(true);
      setRepo(""); setPr("");
      setTimeout(onTriggered, 1500);
      setTimeout(() => setOk(false), 4000);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Failed to start review");
    } finally {
      setBusy(false);
    }
  };

  return (
    <form onSubmit={submit} className="panel flex flex-col gap-3 rounded-2xl p-4 sm:flex-row sm:items-center">
      <div className="flex items-center gap-2 pr-1">
        <Radar className="h-4 w-4 text-accent-soft" />
        <span className="eyebrow !text-[10px] hidden sm:block">Scan a PR</span>
      </div>
      <input
        value={repo} onChange={(e) => setRepo(e.target.value)} placeholder="owner/repo  ·  or paste a PR URL"
        className="h-10 flex-1 rounded-lg border border-border bg-black/30 px-3 font-mono text-sm text-slate-100 placeholder:text-slate-600 focus:outline-none focus:ring-2 focus:ring-accent/40"
      />
      <input
        value={pr} onChange={(e) => setPr(e.target.value)} placeholder="PR #" inputMode="numeric"
        className="h-10 w-full rounded-lg border border-border bg-black/30 px-3 font-mono text-sm text-slate-100 placeholder:text-slate-600 focus:outline-none focus:ring-2 focus:ring-accent/40 sm:w-24"
      />
      <button
        type="submit" disabled={busy}
        className="inline-flex h-10 items-center justify-center gap-2 rounded-lg bg-accent px-5 text-sm font-semibold text-white shadow-glow transition-all hover:bg-accent-deep disabled:opacity-50"
      >
        {busy ? <Loader2 className="h-4 w-4 animate-spin" /> : <Radar className="h-4 w-4" />}
        Run review
      </button>
      {error && <span className="text-xs text-sev-critical">{error}</span>}
      {ok && <span className="text-xs text-safe">Review started — watch the feed.</span>}
    </form>
  );
}

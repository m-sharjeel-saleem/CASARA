"use client";

import { Loader2, Play } from "lucide-react";
import { useState } from "react";

import { api } from "@/lib/api";

export function TriggerBar({ onTriggered }: { onTriggered: () => void }) {
  const [repo, setRepo] = useState("");
  const [pr, setPr] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const submit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!repo.trim() || !pr.trim()) return;
    setBusy(true);
    setError(null);
    try {
      await api.triggerReview(repo.trim(), parseInt(pr, 10));
      setTimeout(onTriggered, 1500);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Failed");
    } finally {
      setBusy(false);
    }
  };

  return (
    <form onSubmit={submit} className="glass flex flex-col gap-3 rounded-2xl p-4 sm:flex-row sm:items-center">
      <input
        value={repo}
        onChange={(e) => setRepo(e.target.value)}
        placeholder="owner/repo"
        className="h-10 flex-1 rounded-lg border border-border bg-black/30 px-3 font-mono text-sm text-zinc-100 placeholder:text-zinc-600 focus:outline-none focus:ring-2 focus:ring-accent/40"
      />
      <input
        value={pr}
        onChange={(e) => setPr(e.target.value)}
        placeholder="PR #"
        className="h-10 w-full rounded-lg border border-border bg-black/30 px-3 font-mono text-sm text-zinc-100 placeholder:text-zinc-600 focus:outline-none focus:ring-2 focus:ring-accent/40 sm:w-28"
      />
      <button
        type="submit"
        disabled={busy}
        className="inline-flex h-10 items-center justify-center gap-2 rounded-lg bg-gradient-to-r from-accent to-safe px-5 text-sm font-medium text-bg transition-all hover:brightness-110 disabled:opacity-50"
      >
        {busy ? <Loader2 className="h-4 w-4 animate-spin" /> : <Play className="h-4 w-4" />}
        Review PR
      </button>
      {error && <span className="text-xs text-danger">{error}</span>}
    </form>
  );
}

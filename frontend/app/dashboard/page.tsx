"use client";

import { ShieldX } from "lucide-react";
import { useCallback, useEffect, useState } from "react";

import { Header } from "@/components/Header";
import { ReviewCard } from "@/components/ReviewCard";
import { StatsBar } from "@/components/StatsBar";
import { TriggerBar } from "@/components/TriggerBar";
import { API_BASE, api } from "@/lib/api";
import type { Review, Stats } from "@/lib/types";

export default function Dashboard() {
  const [reviews, setReviews] = useState<Review[]>([]);
  const [stats, setStats] = useState<Stats | null>(null);
  const [live, setLive] = useState(false);
  const [err, setErr] = useState<string | null>(null);

  const refresh = useCallback(async () => {
    try {
      const [r, s] = await Promise.all([api.reviews(), api.stats()]);
      setReviews(r);
      setStats(s);
      setErr(null);
    } catch {
      setErr(`Cannot reach the CASARA API at ${API_BASE}. Is the backend running?`);
    }
  }, []);

  useEffect(() => {
    refresh();
    const es = new EventSource(`${API_BASE}/api/events`);
    es.onopen = () => setLive(true);
    es.onerror = () => setLive(false);
    const onChange = () => refresh();
    es.addEventListener("review.started", onChange);
    es.addEventListener("review.completed", onChange);
    return () => es.close();
  }, [refresh]);

  return (
    <>
      <Header live={live} />
      <main className="mx-auto max-w-5xl px-5 pb-24">
        <section className="py-10 text-center sm:py-14">
          <h1 className="mx-auto max-w-2xl text-balance text-3xl font-bold tracking-tight sm:text-5xl">
            <span className="text-gradient">Automated security review</span> for every pull request
          </h1>
          <p className="mx-auto mt-4 max-w-xl text-[15px] leading-relaxed text-zinc-400">
            Scanner-grounded multi-agent analysis with a composite risk score and automatic merge
            gating — delivered as inline GitHub comments and tracked here.
          </p>
        </section>

        <div className="space-y-4">
          <TriggerBar onTriggered={refresh} />
          <StatsBar stats={stats} />

          {err && (
            <div className="flex items-center gap-2 rounded-xl border border-danger/30 bg-danger/10 px-4 py-3 text-sm text-danger">
              <ShieldX className="h-4 w-4" /> {err}
            </div>
          )}

          <div className="space-y-3 pt-2">
            <h2 className="text-xs font-semibold uppercase tracking-[0.2em] text-zinc-500">Recent Reviews</h2>
            {reviews.length === 0 && !err ? (
              <div className="glass rounded-2xl py-12 text-center text-sm text-zinc-500">
                No reviews yet. Trigger one above, or open a PR on a connected repository.
              </div>
            ) : (
              reviews.map((r) => <ReviewCard key={r.id} review={r} />)
            )}
          </div>
        </div>
      </main>
    </>
  );
}

"use client";

import { Radar, ShieldX } from "lucide-react";
import { useCallback, useEffect, useMemo, useState } from "react";

import { FilterBar, type ReviewFilter } from "@/components/FilterBar";
import { Header } from "@/components/Header";
import { MetricsPanel } from "@/components/MetricsPanel";
import { ReviewCard } from "@/components/ReviewCard";
import { TriggerBar } from "@/components/TriggerBar";
import { API_BASE, api } from "@/lib/api";
import type { Review, Stats } from "@/lib/types";

export default function Dashboard() {
  const [reviews, setReviews] = useState<Review[]>([]);
  const [stats, setStats] = useState<Stats | null>(null);
  const [live, setLive] = useState(false);
  const [loading, setLoading] = useState(true);
  const [err, setErr] = useState<string | null>(null);
  const [query, setQuery] = useState("");
  const [filter, setFilter] = useState<ReviewFilter>("all");

  const refresh = useCallback(async () => {
    try {
      const [r, s] = await Promise.all([api.reviews(), api.stats()]);
      setReviews(r); setStats(s); setErr(null);
    } catch {
      setErr(`Can't reach the CASARA API at ${API_BASE}. Confirm the backend is running and NEXT_PUBLIC_API_URL is set.`);
    } finally {
      setLoading(false);
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

  const counts = useMemo(() => ({
    all: reviews.length,
    blocked: reviews.filter((r) => r.gated).length,
    passed: reviews.filter((r) => !r.gated && r.status === "completed").length,
  }), [reviews]);

  const visible = useMemo(() => reviews.filter((r) => {
    if (filter === "blocked" && !r.gated) return false;
    if (filter === "passed" && (r.gated || r.status !== "completed")) return false;
    const q = query.trim().toLowerCase();
    if (q && !`${r.repo} ${r.pr_title}`.toLowerCase().includes(q)) return false;
    return true;
  }), [reviews, filter, query]);

  return (
    <>
      <Header live={live} />
      <main className="mx-auto max-w-7xl px-5 pb-24 pt-8">
        <div className="mb-6">
          <div className="eyebrow mb-1.5">Security Console</div>
          <h1 className="font-display text-2xl font-bold tracking-tight text-white sm:text-3xl">
            Pull-request <span className="text-gradient">threat radar</span>
          </h1>
        </div>

        <div className="space-y-5">
          <TriggerBar onTriggered={refresh} />

          {loading ? (
            <div className="grid grid-cols-1 gap-4 lg:grid-cols-12">
              <div className="skeleton h-32 rounded-2xl lg:col-span-3" />
              <div className="skeleton h-32 rounded-2xl lg:col-span-4" />
              <div className="skeleton h-32 rounded-2xl lg:col-span-2" />
              <div className="skeleton h-32 rounded-2xl lg:col-span-3" />
              <div className="skeleton h-24 rounded-2xl lg:col-span-12" />
            </div>
          ) : (
            <MetricsPanel stats={stats} reviews={reviews} />
          )}

          {err && (
            <div className="flex items-start gap-2 rounded-xl border border-sev-critical/30 bg-sev-critical/10 px-4 py-3 text-sm text-sev-critical">
              <ShieldX className="mt-0.5 h-4 w-4 shrink-0" /> {err}
            </div>
          )}

          <div className="pt-2">
            <div className="mb-3 flex items-center gap-2">
              <Radar className="h-4 w-4 text-accent-soft" />
              <h2 className="eyebrow">Live review feed</h2>
            </div>

            {!loading && reviews.length > 0 && (
              <div className="mb-4">
                <FilterBar query={query} setQuery={setQuery} filter={filter} setFilter={setFilter} counts={counts} />
              </div>
            )}

            {loading ? (
              <div className="space-y-3">
                {[0, 1, 2].map((i) => <div key={i} className="skeleton h-20 rounded-2xl" />)}
              </div>
            ) : reviews.length === 0 && !err ? (
              <div className="panel rounded-2xl py-16 text-center">
                <Radar className="mx-auto h-8 w-8 text-slate-600" />
                <p className="mt-3 text-sm text-slate-400">No reviews yet.</p>
                <p className="mt-1 text-xs text-slate-600">
                  Run a review above, or open a pull request on a connected repository.
                </p>
              </div>
            ) : visible.length === 0 ? (
              <p className="py-8 text-center text-sm text-slate-500">No reviews match your filter.</p>
            ) : (
              <div className="space-y-3">
                {visible.map((r, i) => <ReviewCard key={r.id} review={r} index={i} />)}
              </div>
            )}
          </div>
        </div>
      </main>
    </>
  );
}

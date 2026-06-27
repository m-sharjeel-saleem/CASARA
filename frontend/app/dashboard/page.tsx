"use client";

import { ArrowRight, Radar, ShieldX } from "lucide-react";
import Link from "next/link";

import { ConnectionStatus } from "@/components/ConnectionStatus";
import { MetricsPanel } from "@/components/MetricsPanel";
import { PageHeader } from "@/components/PageHeader";
import { ReviewCard } from "@/components/ReviewCard";
import { TriggerBar } from "@/components/TriggerBar";
import { API_BASE } from "@/lib/api";
import { useLiveFeed, useReviews, useStats } from "@/lib/hooks";

export default function Overview() {
  const { data: reviews = [], error, isLoading, mutate } = useReviews();
  const { data: stats } = useStats();
  useLiveFeed();

  return (
    <>
      <PageHeader eyebrow="Security Console" title={<>Pull-request <span className="text-gradient">threat radar</span></>} />

      <ConnectionStatus />

      <div className="space-y-5">
        <TriggerBar onTriggered={() => mutate()} />

        {isLoading ? (
          <div className="grid grid-cols-1 gap-4 lg:grid-cols-12">
            <div className="skeleton h-32 rounded-2xl lg:col-span-3" />
            <div className="skeleton h-32 rounded-2xl lg:col-span-4" />
            <div className="skeleton h-32 rounded-2xl lg:col-span-2" />
            <div className="skeleton h-32 rounded-2xl lg:col-span-3" />
            <div className="skeleton h-24 rounded-2xl lg:col-span-12" />
          </div>
        ) : (
          <MetricsPanel stats={stats ?? null} reviews={reviews} />
        )}

        {error && (
          <div className="flex items-start gap-2 rounded-xl border border-sev-critical/30 bg-sev-critical/10 px-4 py-3 text-sm text-sev-critical">
            <ShieldX className="mt-0.5 h-4 w-4 shrink-0" />
            Can&apos;t reach the CASARA API at {API_BASE}. Confirm the backend is running and NEXT_PUBLIC_API_URL is set.
          </div>
        )}

        <div className="pt-2">
          <div className="mb-3 flex items-center justify-between">
            <div className="flex items-center gap-2">
              <Radar className="h-4 w-4 text-accent-soft" />
              <h2 className="eyebrow">Recent reviews</h2>
            </div>
            <Link href="/dashboard/reviews" className="inline-flex items-center gap-1 text-xs text-accent-soft hover:text-white">
              View all <ArrowRight className="h-3.5 w-3.5" />
            </Link>
          </div>

          {isLoading ? (
            <div className="space-y-3">{[0, 1, 2].map((i) => <div key={i} className="skeleton h-20 rounded-2xl" />)}</div>
          ) : reviews.length === 0 && !error ? (
            <div className="panel rounded-2xl py-16 text-center">
              <Radar className="mx-auto h-8 w-8 text-slate-600" />
              <p className="mt-3 text-sm text-slate-400">No reviews yet.</p>
              <p className="mt-1 text-xs text-slate-600">Open a PR on a connected repo, comment <code className="text-accent-soft">@casara review</code>, or run one above.</p>
            </div>
          ) : (
            <div className="space-y-3">
              {reviews.slice(0, 5).map((r, i) => <ReviewCard key={r.id} review={r} index={i} />)}
            </div>
          )}
        </div>
      </div>
    </>
  );
}

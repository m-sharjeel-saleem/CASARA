"use client";

import { Radar } from "lucide-react";
import { useMemo, useState } from "react";

import { FilterBar, type ReviewFilter } from "@/components/FilterBar";
import { PageHeader } from "@/components/PageHeader";
import { ReviewCard } from "@/components/ReviewCard";
import { useLiveFeed, useReviews } from "@/lib/hooks";

export default function ReviewsPage() {
  const { data: reviews = [], isLoading } = useReviews();
  useLiveFeed();
  const [query, setQuery] = useState("");
  const [filter, setFilter] = useState<ReviewFilter>("all");

  const counts = useMemo(() => ({
    all: reviews.length,
    blocked: reviews.filter((r) => r.gated).length,
    passed: reviews.filter((r) => !r.gated && r.status === "completed").length,
  }), [reviews]);

  const visible = useMemo(() => reviews.filter((r) => {
    if (filter === "blocked" && !r.gated) return false;
    if (filter === "passed" && (r.gated || r.status !== "completed")) return false;
    const q = query.trim().toLowerCase();
    if (q && !`${r.repo} ${r.pr_title} ${r.author}`.toLowerCase().includes(q)) return false;
    return true;
  }), [reviews, filter, query]);

  return (
    <>
      <PageHeader eyebrow="History" title="All reviews" />
      <div className="mb-4">
        <FilterBar query={query} setQuery={setQuery} filter={filter} setFilter={setFilter} counts={counts} />
      </div>

      {isLoading ? (
        <div className="space-y-3">{[0, 1, 2, 3].map((i) => <div key={i} className="skeleton h-20 rounded-2xl" />)}</div>
      ) : visible.length === 0 ? (
        <div className="panel rounded-2xl py-16 text-center">
          <Radar className="mx-auto h-8 w-8 text-slate-600" />
          <p className="mt-3 text-sm text-slate-400">
            {reviews.length === 0 ? "No reviews yet." : "No reviews match your filter."}
          </p>
        </div>
      ) : (
        <div className="space-y-3">
          {visible.map((r, i) => <ReviewCard key={r.id} review={r} index={i} />)}
        </div>
      )}
    </>
  );
}

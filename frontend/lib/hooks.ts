"use client";

import { useEffect, useState } from "react";
import useSWR, { useSWRConfig } from "swr";

import { API_BASE, fetcher } from "./api";
import type { Installation, Review, Stats } from "./types";

const opts = { revalidateOnFocus: false, dedupingInterval: 4000 };

export function useReviews() {
  return useSWR<Review[]>("/api/reviews", fetcher, opts);
}
export function useStats() {
  return useSWR<Stats>("/api/stats", fetcher, opts);
}
export function useReview(id: string | null) {
  return useSWR<Review>(id ? `/api/reviews/${id}` : null, fetcher, opts);
}
export function useInstallations() {
  return useSWR<Installation[]>("/api/installations", fetcher, opts);
}

/** Subscribe to the backend SSE feed and revalidate review/stat queries on events.
 *  Returns whether the stream is currently connected. */
export function useLiveFeed(onEvent?: () => void) {
  const { mutate } = useSWRConfig();
  useEffect(() => {
    const es = new EventSource(`${API_BASE}/api/events`);
    const refresh = () => {
      mutate("/api/reviews");
      mutate("/api/stats");
      onEvent?.();
    };
    es.addEventListener("review.started", refresh);
    es.addEventListener("review.completed", refresh);
    return () => es.close();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);
}

/** Live-connection indicator as its own hook (separate EventSource for the header dot). */
export function useLiveStatus() {
  const [live, setLive] = useState(false);
  useEffect(() => {
    const es = new EventSource(`${API_BASE}/api/events`);
    es.onopen = () => setLive(true);
    es.onerror = () => setLive(false);
    return () => es.close();
  }, []);
  return live;
}

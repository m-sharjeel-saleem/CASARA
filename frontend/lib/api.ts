import type { Review, Stats } from "./types";

export const API_BASE = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

async function get<T>(path: string): Promise<T> {
  const res = await fetch(`${API_BASE}${path}`, { cache: "no-store" });
  if (!res.ok) throw new Error(`Request failed (${res.status})`);
  return res.json() as Promise<T>;
}

export const api = {
  installUrl: () => get<{ configured: boolean; url: string | null }>("/api/install"),
  stats: () => get<Stats>("/api/stats"),
  reviews: () => get<Review[]>("/api/reviews"),
  review: (id: string) => get<Review>(`/api/reviews/${id}`),
  triggerReview: async (repo: string, prNumber?: number) => {
    const res = await fetch(`${API_BASE}/api/review/run`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ repo, pr_number: prNumber ?? null }),
    });
    if (!res.ok) {
      const d = await res.json().catch(() => null);
      throw new Error(d?.detail ?? `Trigger failed (${res.status})`);
    }
    return res.json();
  },
};

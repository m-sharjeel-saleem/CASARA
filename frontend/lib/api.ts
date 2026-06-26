import type { CasaraConfig, Installation, Review, Stats, TriageStatus } from "./types";

export const API_BASE = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

async function get<T>(path: string): Promise<T> {
  const res = await fetch(`${API_BASE}${path}`, { cache: "no-store" });
  if (!res.ok) throw new Error(`Request failed (${res.status})`);
  return res.json() as Promise<T>;
}

/** SWR fetcher — keyed by path. */
export const fetcher = <T>(path: string) => get<T>(path);

export const api = {
  installUrl: () => get<{ configured: boolean; url: string | null }>("/api/install"),
  installations: () => get<Installation[]>("/api/installations"),
  stats: () => get<Stats>("/api/stats"),
  reviews: () => get<Review[]>("/api/reviews"),
  review: (id: string) => get<Review>(`/api/reviews/${id}`),
  config: (installationId: number) => get<CasaraConfig>(`/api/config?installation_id=${installationId}`),

  triageFinding: async (reviewId: string, idx: number, status: TriageStatus) => {
    const res = await fetch(`${API_BASE}/api/reviews/${reviewId}/findings/${idx}`, {
      method: "PUT",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ status }),
    });
    if (!res.ok) throw new Error(`Triage failed (${res.status})`);
    return res.json() as Promise<Review>;
  },

  saveConfig: async (installationId: number, config: CasaraConfig) => {
    const res = await fetch(`${API_BASE}/api/config`, {
      method: "PUT",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ installation_id: installationId, config }),
    });
    if (!res.ok) {
      const d = await res.json().catch(() => null);
      throw new Error(d?.detail ?? `Save failed (${res.status})`);
    }
    return res.json();
  },

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

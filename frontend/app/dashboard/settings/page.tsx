"use client";

import { Check, Loader2, Plus, Save, Trash2 } from "lucide-react";
import { useEffect, useMemo, useState } from "react";

import { PageHeader } from "@/components/PageHeader";
import { api } from "@/lib/api";
import { useInstallations } from "@/lib/hooks";
import type { CasaraConfig, PathRule, Severity } from "@/lib/types";

const DEFAULT_CONFIG: CasaraConfig = {
  version: 1, languages: [], rules: [],
  gate: { level: "error", threshold: 7 },
  noise: { max_comments: 10, min_confidence: "LOW" },
  severity_overrides: {}, semgrep_config: "",
};

const LANGS = ["python", "javascript", "typescript", "go", "ruby", "php", "java", "rust", "c", "csharp"];
const SEVS: Severity[] = ["critical", "high", "medium", "low", "info"];

/** Minimal YAML serializer for the known config shape (preview only). */
function toYaml(c: CasaraConfig): string {
  const L: string[] = ["version: 1"];
  if (c.languages.length) L.push(`languages: [${c.languages.join(", ")}]`);
  L.push("gate:", `  level: ${c.gate.level}`, `  threshold: ${c.gate.threshold}`);
  L.push("noise:", `  max_comments: ${c.noise.max_comments}`, `  min_confidence: ${c.noise.min_confidence}`);
  if (c.semgrep_config) L.push(`semgrep_config: "${c.semgrep_config}"`);
  if (c.rules.length) {
    L.push("rules:");
    for (const r of c.rules) {
      L.push(`  - path: "${r.path}"`, `    instructions: "${r.instructions.replace(/"/g, "'")}"`);
      if (r.severity) L.push(`    severity: ${r.severity}`);
    }
  }
  const ov = Object.entries(c.severity_overrides);
  if (ov.length) { L.push("severity_overrides:"); ov.forEach(([k, v]) => L.push(`  ${k}: ${v}`)); }
  return L.join("\n");
}

const fieldCls = "h-9 rounded-lg border border-border bg-black/30 px-3 text-sm text-slate-100 focus:outline-none focus:ring-2 focus:ring-accent/40";

export default function SettingsPage() {
  const { data: installations = [], isLoading: instLoading } = useInstallations();
  const [iid, setIid] = useState<number | null>(null);
  const [cfg, setCfg] = useState<CasaraConfig>(DEFAULT_CONFIG);
  const [loading, setLoading] = useState(false);
  const [saving, setSaving] = useState(false);
  const [saved, setSaved] = useState(false);
  const [err, setErr] = useState<string | null>(null);

  useEffect(() => { if (iid === null && installations.length) setIid(installations[0].id); }, [installations, iid]);
  useEffect(() => {
    if (iid === null) return;
    setLoading(true);
    api.config(iid).then((c) => setCfg({ ...DEFAULT_CONFIG, ...c }))
      .catch(() => setErr("Could not load config")).finally(() => setLoading(false));
  }, [iid]);

  const yaml = useMemo(() => toYaml(cfg), [cfg]);

  const set = <K extends keyof CasaraConfig>(k: K, v: CasaraConfig[K]) => setCfg((p) => ({ ...p, [k]: v }));
  const toggleLang = (l: string) =>
    set("languages", cfg.languages.includes(l) ? cfg.languages.filter((x) => x !== l) : [...cfg.languages, l]);
  const addRule = () => set("rules", [...cfg.rules, { path: "**/*", instructions: "", severity: null }]);
  const updateRule = (i: number, patch: Partial<PathRule>) =>
    set("rules", cfg.rules.map((r, j) => (j === i ? { ...r, ...patch } : r)));
  const removeRule = (i: number) => set("rules", cfg.rules.filter((_, j) => j !== i));

  const save = async () => {
    if (iid === null) return;
    setSaving(true); setErr(null); setSaved(false);
    try { await api.saveConfig(iid, cfg); setSaved(true); setTimeout(() => setSaved(false), 3000); }
    catch (e) { setErr(e instanceof Error ? e.message : "Save failed"); }
    finally { setSaving(false); }
  };

  if (instLoading) return <><PageHeader eyebrow="Configuration" title="Settings & Rules" /><div className="skeleton h-80 rounded-2xl" /></>;
  if (installations.length === 0) {
    return (
      <>
        <PageHeader eyebrow="Configuration" title="Settings & Rules" />
        <div className="panel rounded-2xl py-16 text-center">
          <p className="text-sm text-slate-400">Install CASARA on a repository first to configure rules.</p>
        </div>
      </>
    );
  }

  return (
    <>
      <PageHeader eyebrow="Configuration" title="Settings & Rules">
        {installations.length > 1 && (
          <select value={iid ?? ""} onChange={(e) => setIid(Number(e.target.value))} className={fieldCls}>
            {installations.map((i) => <option key={i.id} value={i.id}>{i.account}</option>)}
          </select>
        )}
        <button onClick={save} disabled={saving}
          className="inline-flex h-9 items-center gap-2 rounded-lg bg-accent px-4 text-sm font-semibold text-white shadow-glow transition hover:bg-accent-deep disabled:opacity-50">
          {saving ? <Loader2 className="h-4 w-4 animate-spin" /> : saved ? <Check className="h-4 w-4" /> : <Save className="h-4 w-4" />}
          {saved ? "Saved" : "Save"}
        </button>
      </PageHeader>

      <p className="mb-5 text-[13px] text-slate-400">
        These are your org-wide defaults — they apply to every review automatically. A repo&apos;s own
        <code className="mx-1 text-accent-soft">.casara.yml</code> overrides them. No file commit needed.
      </p>
      {err && <div className="mb-4 rounded-lg border border-sev-critical/30 bg-sev-critical/10 px-4 py-2.5 text-sm text-sev-critical">{err}</div>}

      <div className={`grid gap-5 lg:grid-cols-2 ${loading ? "opacity-50" : ""}`}>
        <div className="space-y-5">
          {/* Languages */}
          <section className="panel rounded-2xl p-5">
            <h2 className="eyebrow mb-1">Languages</h2>
            <p className="mb-3 text-[12px] text-slate-500">Scope analysis (none = all). Config/manifest files always scanned.</p>
            <div className="flex flex-wrap gap-2">
              {LANGS.map((l) => (
                <button key={l} onClick={() => toggleLang(l)}
                  className={`rounded-full border px-3 py-1 text-xs transition ${cfg.languages.includes(l)
                    ? "border-accent/40 bg-accent/15 text-accent-soft" : "border-border text-slate-400 hover:text-slate-200"}`}>
                  {l}
                </button>
              ))}
            </div>
          </section>

          {/* Gate + noise */}
          <section className="panel rounded-2xl p-5">
            <h2 className="eyebrow mb-3">Merge gate & noise</h2>
            <div className="grid grid-cols-2 gap-3">
              <label className="flex flex-col gap-1 text-[12px] text-slate-400">Gate level
                <select value={cfg.gate.level} onChange={(e) => set("gate", { ...cfg.gate, level: e.target.value as CasaraConfig["gate"]["level"] })} className={fieldCls}>
                  <option value="off">off — never block</option>
                  <option value="warning">warning — surface only</option>
                  <option value="error">error — block merges</option>
                </select>
              </label>
              <label className="flex flex-col gap-1 text-[12px] text-slate-400">Risk threshold ({cfg.gate.threshold})
                <input type="range" min={0} max={10} step={0.5} value={cfg.gate.threshold}
                  onChange={(e) => set("gate", { ...cfg.gate, threshold: Number(e.target.value) })} className="mt-2.5 accent-accent" />
              </label>
              <label className="flex flex-col gap-1 text-[12px] text-slate-400">Max comments / PR
                <input type="number" min={1} max={50} value={cfg.noise.max_comments}
                  onChange={(e) => set("noise", { ...cfg.noise, max_comments: Number(e.target.value) })} className={fieldCls} />
              </label>
              <label className="flex flex-col gap-1 text-[12px] text-slate-400">Min confidence
                <select value={cfg.noise.min_confidence} onChange={(e) => set("noise", { ...cfg.noise, min_confidence: e.target.value as CasaraConfig["noise"]["min_confidence"] })} className={fieldCls}>
                  <option value="LOW">LOW (show all)</option>
                  <option value="MEDIUM">MEDIUM</option>
                  <option value="HIGH">HIGH (strict)</option>
                </select>
              </label>
            </div>
            <label className="mt-3 flex flex-col gap-1 text-[12px] text-slate-400">Custom Semgrep ruleset (optional)
              <input value={cfg.semgrep_config} onChange={(e) => set("semgrep_config", e.target.value)}
                placeholder="p/owasp-top-ten  or  ci/rules/" className={`${fieldCls} font-mono`} />
            </label>
          </section>

          {/* Custom NL rules */}
          <section className="panel rounded-2xl p-5">
            <div className="mb-1 flex items-center justify-between">
              <h2 className="eyebrow">Custom rules</h2>
              <button onClick={addRule} className="inline-flex items-center gap-1 text-xs text-accent-soft hover:text-white">
                <Plus className="h-3.5 w-3.5" /> Add rule
              </button>
            </div>
            <p className="mb-3 text-[12px] text-slate-500">Plain-English rules the AI enforces, scoped to a path glob.</p>
            <div className="space-y-3">
              {cfg.rules.length === 0 && <p className="text-xs text-slate-600">No custom rules yet.</p>}
              {cfg.rules.map((r, i) => (
                <div key={i} className="rounded-lg border border-border bg-black/20 p-3">
                  <div className="flex items-center gap-2">
                    <input value={r.path} onChange={(e) => updateRule(i, { path: e.target.value })}
                      placeholder="src/auth/**" className={`${fieldCls} w-40 font-mono`} />
                    <select value={r.severity ?? ""} onChange={(e) => updateRule(i, { severity: (e.target.value || null) as Severity | null })} className={fieldCls}>
                      <option value="">no floor</option>
                      {SEVS.map((s) => <option key={s} value={s}>{s}</option>)}
                    </select>
                    <button onClick={() => removeRule(i)} className="ml-auto text-slate-500 hover:text-sev-critical"><Trash2 className="h-4 w-4" /></button>
                  </div>
                  <textarea value={r.instructions} onChange={(e) => updateRule(i, { instructions: e.target.value })}
                    placeholder="e.g. Require parameterized SQL; flag any string-built queries."
                    rows={2} className="mt-2 w-full rounded-lg border border-border bg-black/30 px-3 py-2 text-sm text-slate-100 focus:outline-none focus:ring-2 focus:ring-accent/40" />
                </div>
              ))}
            </div>
          </section>
        </div>

        {/* Live YAML preview */}
        <div className="lg:sticky lg:top-7 lg:self-start">
          <section className="panel rounded-2xl p-5">
            <h2 className="eyebrow mb-3">Effective config (.casara.yml)</h2>
            <pre className="max-h-[70vh] overflow-auto rounded-lg border border-border bg-black/40 p-4 font-mono text-[12px] leading-relaxed text-slate-300">{yaml}</pre>
            <p className="mt-3 text-[11px] text-slate-500">This is what the reviewer applies. Saving stores it as your org default.</p>
          </section>
        </div>
      </div>
    </>
  );
}

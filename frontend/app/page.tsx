import { Bot, GitPullRequest, PackageX, Radar, ShieldCheck, Sparkles, SlidersHorizontal, Wrench } from "lucide-react";
import Link from "next/link";

import { InstallButton } from "@/components/InstallButton";

const FEATURES = [
  { icon: Bot, title: "AI-code aware",
    body: "A dedicated agent hunts the mistakes AI assistants make most — string-built SQL, disabled TLS, leaked secrets, hallucinated packages, poisoned editor-rules files." },
  { icon: PackageX, title: "Stops supply-chain worms",
    body: "Flags install-time scripts and known-malicious dependencies — the exact vector behind the npm worms that hit 25,000+ repos — before they ever run." },
  { icon: Wrench, title: "One-click fixes",
    body: "Doesn't just complain. CASARA posts GitHub suggested-change blocks so you apply the fix in a single click, right inside the PR." },
  { icon: ShieldCheck, title: "Hybrid grounding",
    body: "Deterministic scanners cross-validate the AI findings, and a critic agent drops false positives — so you get signal, not noise." },
  { icon: SlidersHorizontal, title: "Your rules, your policy",
    body: "A .casara.yml sets per-path rules, custom Semgrep packs, language scope, severity overrides, and gate levels — the engine enforces them." },
  { icon: GitPullRequest, title: "Merge gating",
    body: "A composite risk score blocks a PR on any critical or verified-high finding — wired straight into branch protection." },
];

const STATS = [
  { n: "45%", l: "of AI-generated code shipped with a security flaw — Veracode, 2025" },
  { n: "2.74×", l: "more security issues in AI-authored pull requests — CodeRabbit" },
  { n: "19.7%", l: "of AI-recommended packages don't exist (slopsquatting) — USENIX 2025" },
];

export default function Landing() {
  return (
    <main className="mx-auto max-w-6xl px-5">
      <header className="flex items-center justify-between py-6">
        <Link href="/" className="flex items-center gap-2.5">
          {/* eslint-disable-next-line @next/next/no-img-element */}
          <img src="/logo.svg" alt="" className="h-7 w-7" />
          <span className="font-display text-[15px] font-bold tracking-tight text-white">CASARA</span>
        </Link>
        <nav className="flex items-center gap-5 text-sm text-slate-400">
          <Link href="/dashboard" className="transition hover:text-white">Console</Link>
          <InstallButton size="sm" />
        </nav>
      </header>

      {/* Hero — radar thesis */}
      <section className="relative overflow-hidden py-20 sm:py-28">
        <div className="radar-sweep pointer-events-none absolute left-1/2 top-1/2 -z-10 h-[640px] w-[640px] -translate-x-1/2 -translate-y-1/2 overflow-hidden rounded-full opacity-50" />
        <div className="pointer-events-none absolute left-1/2 top-1/2 -z-10 h-[420px] w-[420px] -translate-x-1/2 -translate-y-1/2 rounded-full border border-accent/10" />
        <div className="pointer-events-none absolute left-1/2 top-1/2 -z-10 h-[620px] w-[620px] -translate-x-1/2 -translate-y-1/2 rounded-full border border-accent/5" />

        <div className="text-center">
          <div className="mx-auto mb-6 inline-flex items-center gap-2 rounded-full border border-border bg-white/[0.03] px-4 py-1.5 text-xs text-slate-300">
            <Radar className="h-3.5 w-3.5 text-accent-soft" /> Security review for the age of AI-written code
          </div>
          <h1 className="mx-auto max-w-3xl text-balance font-display text-4xl font-extrabold leading-[1.05] tracking-tight sm:text-6xl">
            Catch the bugs your <span className="text-gradient">AI wrote</span> before they merge
          </h1>
          <p className="mx-auto mt-6 max-w-xl text-pretty text-[15px] leading-relaxed text-slate-400">
            CASARA reviews every pull request with deterministic scanners <em>and</em> AI agents tuned
            for AI-generated code. It scores the risk, blocks dangerous merges, and opens one-click
            fixes — so a small team ships secure code without a security team.
          </p>
          <div className="mt-9 flex items-center justify-center gap-3">
            <InstallButton />
            <Link href="/dashboard"
              className="rounded-xl border border-border px-6 py-3 text-[15px] font-semibold text-slate-200 transition hover:bg-white/5">
              Open the console
            </Link>
          </div>
        </div>
      </section>

      {/* Proof */}
      <section className="grid gap-4 sm:grid-cols-3">
        {STATS.map((s) => (
          <div key={s.n} className="panel rounded-2xl p-6 text-center">
            <div className="font-display text-3xl font-extrabold text-gradient">{s.n}</div>
            <p className="mt-2 text-xs leading-relaxed text-slate-400">{s.l}</p>
          </div>
        ))}
      </section>

      {/* Features */}
      <section className="py-24">
        <div className="mb-10 text-center">
          <div className="eyebrow mb-2">What it does</div>
          <h2 className="font-display text-2xl font-bold tracking-tight sm:text-3xl">
            A guardrail, not another dashboard to ignore
          </h2>
          <p className="mx-auto mt-3 max-w-lg text-sm text-slate-400">
            Every check runs automatically on the pull request, where your team already works.
          </p>
        </div>
        <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
          {FEATURES.map((f) => (
            <div key={f.title} className="panel group rounded-2xl p-6 transition-shadow hover:shadow-tile">
              <div className="grid h-9 w-9 place-items-center rounded-lg border border-accent/20 bg-accent/10 text-accent-soft">
                <f.icon className="h-5 w-5" />
              </div>
              <h3 className="mt-4 font-display text-sm font-semibold text-white">{f.title}</h3>
              <p className="mt-2 text-[13px] leading-relaxed text-slate-400">{f.body}</p>
            </div>
          ))}
        </div>
      </section>

      {/* CTA */}
      <section className="relative mb-24 overflow-hidden rounded-3xl px-6 py-16 text-center panel">
        <div className="radar-sweep pointer-events-none absolute left-1/2 top-0 -z-10 h-[400px] w-[400px] -translate-x-1/2 overflow-hidden rounded-full opacity-30" />
        <Sparkles className="mx-auto h-6 w-6 text-accent-soft" />
        <h2 className="mt-4 font-display text-2xl font-bold tracking-tight sm:text-3xl">
          Put a security engineer on every PR
        </h2>
        <p className="mx-auto mt-3 max-w-md text-sm text-slate-400">
          Install CASARA on a repo and open a pull request. Your first review runs in seconds.
        </p>
        <div className="mt-8 flex justify-center"><InstallButton /></div>
      </section>

      <footer className="border-t border-border py-8 text-center text-xs text-slate-600">
        CASARA — Contextual Automated Security Analysis &amp; Risk Assessment
      </footer>
    </main>
  );
}

import {
  Bot,
  GitPullRequest,
  PackageX,
  ShieldCheck,
  Sparkles,
  Wrench,
} from "lucide-react";
import Link from "next/link";

import { InstallButton } from "@/components/InstallButton";

const FEATURES = [
  {
    icon: Bot,
    title: "AI-code aware",
    body: "A dedicated agent hunts the mistakes AI assistants make most: string-built SQL, disabled TLS, leaked secrets, hallucinated packages, and poisoned editor rules files.",
  },
  {
    icon: PackageX,
    title: "Stops supply-chain worms",
    body: "Flags install-time scripts and known-malicious dependencies — the exact vector behind the npm worms that hit 25,000+ repos — before they ever run.",
  },
  {
    icon: Wrench,
    title: "One-click fixes",
    body: "Doesn't just complain. CASARA opens GitHub suggested-change blocks so you apply the fix in a single click, right in the PR.",
  },
  {
    icon: GitPullRequest,
    title: "Merge gating",
    body: "A composite risk score blocks a PR from merging on any critical or verified-high finding — wired into branch protection.",
  },
  {
    icon: ShieldCheck,
    title: "Hybrid grounding",
    body: "Deterministic scanners (Semgrep, Bandit, Gitleaks) cross-validate the AI findings, so you get fewer false positives, not more noise.",
  },
  {
    icon: Sparkles,
    title: "Self-serve & transparent",
    body: "Install in two clicks. No sales call, no per-seat trap. Built for small teams the enterprise tools price out.",
  },
];

const STATS = [
  { n: "45%", l: "of AI-generated code shipped with a security flaw (Veracode, 2025)" },
  { n: "2.74×", l: "more security issues in AI-authored pull requests (CodeRabbit)" },
  { n: "28.6M", l: "secrets leaked to GitHub in 2025, +34% YoY (GitGuardian)" },
];

export default function Landing() {
  return (
    <main className="mx-auto max-w-5xl px-5">
      {/* Nav */}
      <header className="flex items-center justify-between py-6">
        <span className="text-sm font-semibold tracking-tight">
          <span className="text-gradient">CASARA</span>
        </span>
        <nav className="flex items-center gap-5 text-sm text-zinc-400">
          <Link href="/dashboard" className="transition hover:text-white">
            Dashboard
          </Link>
          <InstallButton size="sm" />
        </nav>
      </header>

      {/* Hero */}
      <section className="py-16 text-center sm:py-24">
        <div className="mx-auto mb-5 inline-flex items-center gap-2 rounded-full border border-white/10 bg-white/5 px-4 py-1.5 text-xs text-zinc-300">
          <Sparkles className="h-3.5 w-3.5" /> Security review built for the age of AI-written code
        </div>
        <h1 className="mx-auto max-w-3xl text-balance text-4xl font-bold tracking-tight sm:text-6xl">
          Catch the bugs your <span className="text-gradient">AI wrote</span> before they merge
        </h1>
        <p className="mx-auto mt-5 max-w-xl text-pretty text-[15px] leading-relaxed text-zinc-400">
          CASARA reviews every pull request with deterministic scanners <em>and</em> AI agents tuned
          for AI-generated code. It scores the risk, blocks dangerous merges, and opens one-click
          fixes — so a small team ships secure code without a security team.
        </p>
        <div className="mt-8 flex items-center justify-center gap-3">
          <InstallButton />
          <Link
            href="/dashboard"
            className="rounded-xl border border-white/10 px-6 py-3 text-[15px] font-semibold text-zinc-200 transition hover:bg-white/5"
          >
            See the dashboard
          </Link>
        </div>
      </section>

      {/* Proof stats */}
      <section className="grid gap-4 sm:grid-cols-3">
        {STATS.map((s) => (
          <div key={s.n} className="glass rounded-2xl p-6 text-center">
            <div className="text-gradient text-3xl font-bold">{s.n}</div>
            <p className="mt-2 text-xs leading-relaxed text-zinc-400">{s.l}</p>
          </div>
        ))}
      </section>

      {/* Features */}
      <section className="py-20">
        <h2 className="mb-2 text-center text-2xl font-bold tracking-tight sm:text-3xl">
          A guardrail, not another dashboard to ignore
        </h2>
        <p className="mx-auto mb-10 max-w-lg text-center text-sm text-zinc-400">
          Every check runs automatically on the pull request, where your team already works.
        </p>
        <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
          {FEATURES.map((f) => (
            <div key={f.title} className="glass rounded-2xl p-6">
              <f.icon className="h-5 w-5 text-accent" />
              <h3 className="mt-4 text-sm font-semibold">{f.title}</h3>
              <p className="mt-2 text-[13px] leading-relaxed text-zinc-400">{f.body}</p>
            </div>
          ))}
        </div>
      </section>

      {/* CTA */}
      <section className="glass mb-24 rounded-3xl px-6 py-14 text-center">
        <h2 className="text-2xl font-bold tracking-tight sm:text-3xl">
          Put a security engineer on every PR
        </h2>
        <p className="mx-auto mt-3 max-w-md text-sm text-zinc-400">
          Install CASARA on a repo and open a pull request. Your first review runs in seconds.
        </p>
        <div className="mt-7 flex justify-center">
          <InstallButton />
        </div>
      </section>

      <footer className="border-t border-white/5 py-8 text-center text-xs text-zinc-600">
        CASARA — Contextual Automated Security Analysis &amp; Risk Assessment
      </footer>
    </main>
  );
}

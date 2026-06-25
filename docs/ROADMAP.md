# CASARA — Competitive Roadmap (research-backed)

Synthesized from deep web research (Jun 2026): competitor docs (CodeRabbit, Greptile, Qodo,
Semgrep, ast-grep, Cursor BugBot), engineering blogs (Anthropic, LangChain), and security sources
(Socket, Datadog). 25/25 verified claims. This file is the prioritized plan; we build top-down.

## What the market has converged on (table-stakes)

Every serious AI code-review tool now ships these. If CASARA lacks one, it looks incomplete:

1. **Custom rules** — three flavors: per-path natural-language instructions, declarative AST/pattern
   rules, and importable rule packs. (CodeRabbit `path_instructions`, Semgrep YAML, ast-grep, Qodo
   `best_practices.md`.)
2. **One-click autofix** to the PR branch or a stacked PR.  ✅ *CASARA has this (suggestions).*
3. **Bundled deterministic scanners** with good defaults.  ✅ *CASARA has Semgrep/Bandit/Gitleaks/depscan.*
4. **Pre-merge gating** with off/warning/error levels.  ◑ *CASARA gates, but binary (block/pass).*
5. **Language/framework scoping** via a language tag on rules/analyzers.  ◑ *Implicit; no user control.*
6. **Learning from feedback** (preferences derived from PR interactions).  ✗ *Not yet.*
7. **Noise control** — confidence indicators, severity grouping, a hard cap on comments. Greptile's
   benchmark: more coverage (82% vs 44%) but 5x more false positives (~11 vs ~2/run). Elementor caps
   at **5 inline comments per PR** to force prioritization.  ◑ *CASARA caps fixes at 3; no FP filter.*

## Differentiators (bigger bets — where CASARA can win the small-team niche)

8. **AI-generated-code + supply-chain/slopsquatting detection.** Validated: a USENIX 2025 study found
   **19.7% of AI-recommended packages don't exist** (open-source models 21.7%). ✅ *This is already
   CASARA's headline — lean into it harder.*
9. **Context-aware risk scoring** — Likelihood × Impact, adjusted for exploitability (EPSS), prod vs
   non-prod, active-exploit feeds — instead of a static CVSS number. ◑ *CASARA has a composite score;
   can be made smarter.*
10. **Scoped multi-agent architecture** — specialized parallel sub-agents (security, secrets,
    dependency, tests) under an orchestrator, with a **reflection/critic loop grounded in scanner
    output**. Anthropic: orchestrator+subagents beat single-agent by 90.2% on parallelizable work, but
    cost ~15x tokens and are a poor fit for tightly-coupled diffs → **deploy selectively.** ◑ *CASARA
    runs 3 agents sequentially today; upgrade to orchestrated + critic.*
11. **Rule Miner** — learn custom rules from a repo's PR history (Qodo parity). ✗ *Differentiator, high effort.*
12. **Chat-on-PR** — `@casara ask …` to explain a finding or a fix. ✗ *Engagement driver.*

## Your three ideas — verdict from the research

- **(a) User-defined custom rules** → **table-stakes. Build it.** Highest-priority gap.
- **(b) Advanced sub-agent / agentic architecture** → **real differentiator**, but scope it: parallel
  sub-agents for independent concerns + a critic grounded in scanner output. Don't multi-agent every PR.
- **(c) Language/framework selection** → **table-stakes.** Low effort given our scanners are already
  language-aware; just expose it in config.

## Ranked build order (recommended)

### Tier 1 — Quick, high-leverage (do first)
1. **`.casara.yml` config** with **per-path natural-language rules** + **severity overrides** +
   **language scoping** (covers ideas a + c). *Low-med effort, table-stakes, immediate credibility.*
2. **Noise control**: confidence threshold + per-PR comment cap + severity grouping in the comment.
   *Low effort, directly improves trust (the #1 differentiator in benchmarks).*
3. **Gating levels** off/warning/error per category. *Low effort.*

### Tier 2 — Differentiators (next)
4. **Orchestrated sub-agents + critic loop** grounded in scanner findings (upgrade the existing 3
   agents). *Med-high effort, idea (b), cuts false positives.*
5. **Declarative pattern rules** via Semgrep custom-rule passthrough (`.casara.yml` → semgrep `--config`).
   *Med effort, reuses an engine instead of building one.*
6. **Context-aware severity** (EPSS/exploit/prod weighting). *Med effort.*

### Tier 3 — Larger bets (later)
7. **Chat-on-PR** (`@casara ask`). 8. **Learning from feedback.** 9. **Rule Miner from PR history.**
10. **Repo-wide RAG context** (Greptile-style full-codebase awareness).

## Recommendation: build Tier 1 next (1→2→3)

It closes the table-stakes gaps that make CASARA look complete next to CodeRabbit/Qodo, directly
implements two of the user's three ideas, and is all low/medium effort. Then Tier-2 #4 (orchestrated
sub-agents + critic) delivers the "advanced agentic" differentiator the user wants.

## Honest gaps in this research
Dataset skewed toward CodeRabbit; thin on Greptile/Snyk/Socket/Cursor specifics. No independent
(non-vendor) false-positive benchmarks. Free-tier conversion + dashboard UX under-evidenced. Treat
vendor capability claims as directional, not gospel.

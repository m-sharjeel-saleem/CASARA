# CASARA — Build Log

> A running, step-by-step record of everything we build, **why** we build it, and how each piece works.
> This is your learning document. Read it top to bottom and you'll understand the whole product.
> Newest entries are added at the **bottom**.

---

## What CASARA is (the one-paragraph pitch)

**CASARA is an AI-code security guardrail for small teams.** You install it on your GitHub repo as an
app. Every time someone opens a pull request, CASARA reviews the changed code — using both
deterministic scanners (Semgrep, Bandit, Gitleaks) **and** AI agents — scores the risk, and **blocks
the merge** if it finds something dangerous (a leaked secret, a SQL injection, an insecure
AI-generated pattern, a malicious dependency). When it can, it also **opens a fix**.

**Why this can make money (from our market research):**
- AI-written code ships insecure at scale — 45% of AI code had security flaws (Veracode), AI pull
  requests have 2.74× more security issues (CodeRabbit), 28.65M secrets leaked to GitHub in 2025.
- The incumbents that solve this (Snyk, GitGuardian) are **expensive and enterprise-only**. Snyk caps
  its cheap tier at 10 developers; GitGuardian hides pricing behind "contact sales."
- That leaves **small teams and startups** with no affordable, self-serve, AI-native option.
  **That gap is our customer.**

---

## The roadmap (ordered for "earn money")

To have *paying* customers, things must happen in this order. Each phase is a section below; we fill
in the detailed steps as we build them.

| Phase | Goal | Why this order |
|---|---|---|
| **0. Foundation** | Clean repo, build log, fix `.gitignore`, plan the data model for multi-user | You can't add customers to a single-user app; we prepare the ground first. |
| **1. The differentiator** | AI-generated-code detection agent + agentic auto-fix | This is *why* a customer picks us over free tools. Build the value before the storefront. |
| **2. Installable product** | GitHub App (click "Install"), not a manual PAT | A product a stranger can use without us. PAT = no business. |
| **3. Accounts & multi-tenant** | Auth + per-customer data isolation | You can't charge people who aren't separated from each other. |
| **4. Billing** | Usage metering + Stripe tiers (Free / Pro) | The actual money step. |
| **5. Storefront + deploy** | Landing page that sells it + live deployment | So strangers can find it, understand it, and pay. |

> We are optimizing for **revenue**, so we do NOT gold-plate. Every feature is the simplest version
> that lets a customer pay us.

---

## Glossary (terms you'll see a lot)

- **PR (pull request):** a proposed code change on GitHub. CASARA reviews these.
- **SAST:** Static Application Security Testing — scanning source code for bugs without running it.
- **SCA:** Software Composition Analysis — checking your *dependencies* for known-bad packages.
- **Gating:** blocking a PR from merging when it's too risky (via GitHub "commit status").
- **Agent:** an LLM (Gemini) given a focused job and a strict output format.
- **Multi-tenant:** one running app safely serving many separate customers.
- **Webhook:** GitHub calls *our* server when an event (like "PR opened") happens.

---

## Build entries

<!-- New steps appended below this line, newest at the bottom. -->

### Step 0 — Foundation (Phase 0)

**What I did:** Audited the entire existing codebase file-by-file (it's real and working: ~1,150 lines,
11 passing tests, working GitHub/Gemini/scanner integrations). Created this build log. Confirmed
`.gitignore` correctly excludes secrets, `node_modules`, build artifacts, and the local SQLite DB.

**What you should understand:** CASARA already had a solid *engine* — the part that scores risk and
blocks merges. What it lacked was (a) the feature that makes it worth paying for, and (b) everything
needed to actually sell it. So we build value first, storefront later.

---

### Step 1 — The AI-code detection agent (Phase 1, the differentiator)

**The problem it solves:** Generic scanners (Semgrep/Bandit) and a generic "security agent" catch
*generic* bugs. But our market research showed the money is in catching the security mistakes that
**AI coding assistants** make disproportionately. So we added a third AI agent specialized for exactly
those patterns.

**Files touched:**
- `app/agents/prompts.py` — added `AI_CODE_SYSTEM`, a prompt that hunts for 4 specific AI-code failure
  modes: (1) insecure-by-default patterns (string-built SQL, disabled TLS, weak crypto, IDOR, plaintext
  passwords, unsafe deserialization); (2) **hallucinated/typosquatted dependencies** ("slopsquatting" —
  AI inventing package names that attackers then register); (3) leaked secrets in generated code; (4)
  **AI-config poisoning** (hidden malicious instructions in `.cursorrules`/copilot config — the "Rules
  File Backdoor" from our research).
- `app/models.py` — added one field to `Finding`: `ai_signal` (a short phrase saying *why* a finding
  looks AI-generated, e.g. "string-built SQL"). This is what lets us market "AI-code-aware."
- `app/agents/analysis.py` — added `aicode_agent()`. Unlike the other agents it also receives the
  **list of changed file paths**, so it can flag a poisoned `.cursorrules` or a suspicious new import.
- `app/services/review.py` — the orchestrator now runs three agents (security + logic + ai-code).
- `app/core/risk.py` — added `ai-code-agent` to `CODE_SOURCES` so its findings count toward the SAST
  risk dimension and can gate a merge, exactly like the scanners.

**How it stays safe & cheap:** The agent only *adds* findings; it can't lower a score. With no Gemini
key it returns `[]` and the deterministic scanners still work (graceful degradation — verified by a
smoke test). The diff is wrapped in untrusted-content markers so a malicious PR can't prompt-inject it.

**Tests added:** `test_aicode_agent_in_code_sources`, `test_parse_captures_ai_signal`,
`test_aicode_cross_validates_with_scanner`.

---

### Step 2 — Agentic auto-fix (Phase 1, the remediation differentiator)

**The problem it solves:** Our research said incumbents *report* problems but small teams want them
*fixed*. So when CASARA finds a fixable issue, it now posts a one-click **GitHub "suggested change"** —
the author clicks "Apply suggestion" and the fix lands in the PR.

**Files touched:**
- `app/agents/prompts.py` — added `FIX_SYSTEM`: given one finding + the numbered source lines around
  it, the model returns a minimal replacement for a contiguous line range (`start_line`, `end_line`,
  `replacement`, `explanation`).
- `app/agents/autofix.py` *(new)* — `generate(finding, file_source)` builds an 8-line context window
  around the issue, asks the model for a fix, and **validates** the returned range is inside the window
  we showed it (so a hallucinated line number can't corrupt the file). Returns a `Suggestion` or `None`.
  Only attempts fixes for medium+ severity findings that name a file and line.
- `app/services/github.py` — added `post_suggestion()`: posts an inline PR review comment containing a
  ` ```suggestion ` block (GitHub renders the "Apply" button). Handles single-line vs multi-line ranges.
- `app/services/review.py` — added `_post_fixes()`: after posting the review comment, generates and
  posts up to `MAX_AUTOFIXES` suggestions (default 3) for the top findings. File content is re-fetched
  at the PR head so line numbers line up.
- `app/config.py` — added `max_autofixes` (default 3) to cap LLM cost per PR.

**Why the cap matters for "earn money":** every fix is an LLM call = real cost. Capping fixes per PR
keeps our per-review cost predictable, which is what lets us price the product profitably later.

**Tests added:** `test_autofix_skips_low_severity`, `test_autofix_skips_without_file_source`,
`test_autofix_window_numbering`.

**Status after Steps 1-2:** 17 tests passing (was 11). The product now does something no free tool
does for small teams: AI-code-aware review + one-click AI fixes. Next: make it *installable* (GitHub
App) and *multi-tenant* so strangers can pay for it.

---

### Step 3 — Dependency / supply-chain scanner (Phase 1, the worm defense)

**The problem it solves:** Our research's #1 verified threat was **self-propagating npm worms**
(Shai-Hulud: 25,000+ repos) and DPRK GitHub campaigns (PolinRider). They spread by running code at
*install time* (npm `preinstall`/`postinstall` hooks) — *before* any test or scanner runs. The risk
model already reserved an "SCA" (Software Composition Analysis) slot but nothing filled it.

**Files touched:**
- `app/services/depscan.py` *(new)* — a pure-Python scanner (no extra binary, runs anywhere) that
  walks the PR's files and inspects dependency manifests (`package.json`, `requirements.txt`,
  `pyproject.toml`) for three worm/supply-chain red flags:
  1. **Install-time hook scripts** (`preinstall`/`install`/`postinstall`) → HIGH. This is the exact
     Shai-Hulud vector.
  2. **Known-malicious package names** (a small built-in IOC blocklist: `shai-hulud`, compromised
     packages from that campaign) → CRITICAL + auto-verified → hard-blocks the merge.
  3. **Untrusted version sources** (git+/http/github: URLs that bypass registry integrity) → MEDIUM.
- `app/services/scanners.py` — `scan_directory()` now also runs `depscan.scan_dependencies()`.
- `app/core/risk.py` — added `SCA_SOURCES = {"trivy", "depscan"}`; the SCA dimension is now actually
  populated (it was dead code before, always 0).
- `app/services/review.py` — the PR comment table now shows an **"AI signal"** column (🤖) so the
  AI-code-awareness is visible to the user — that's the thing we'll market.

**Why this matters for "earn money":** "We block the npm worm that hit 25,000 repos, at install time,
before it runs" is a concrete, scary, *current* sales line that free tools (Dependabot) don't cover.

**Tests added:** `test_depscan_flags_install_hook`, `test_depscan_flags_known_malicious`,
`test_depscan_flags_untrusted_python_source`, `test_depscan_feeds_sca_dimension`.

**Status after Phase 1:** 21 tests passing. CASARA is now a genuinely differentiated *engine*:
hybrid scanner+AI review, AI-code-specific detection, supply-chain/worm defense, and one-click fixes.
The value is built. **Phase 2 makes it installable by strangers (GitHub App), then multi-tenant + billing.**

> ⚠️ **Honest note on the IOC list:** the malicious-package list in `depscan.py` is a small, static
> starter set. A real product needs a maintained threat-intel feed (one of the open questions from our
> research). For launch it's fine; flag it as a "known limitation / roadmap" item.

---

### Step 4 — GitHub App (Phase 2, the "installable by strangers" step)

**The problem it solves:** A Personal Access Token (PAT) is *your* personal credential — it can't be
the basis of a product other people use. A **GitHub App** is installed per-org/repo and CASARA
authenticates *as each installation*. This is the single change that turns CASARA from a personal
script into a multi-tenant product someone can click "Install" on. (You decided: get it installable
first, add billing later.)

**How GitHub App auth works (worth understanding):**
1. The App has a **private key**. We sign a short-lived **JWT** with it (RS256) — that proves "we are
   this App."
2. We exchange that JWT for an **installation access token** scoped to *one* customer's repos.
3. We use that token for API calls on that installation's behalf. Tokens last ~1h, so we cache them.

**Files touched:**
- `app/services/gh_app.py` *(new)* — `installation_token(installation_id)` (JWT → token, cached until
  near expiry) and `list_installations()`. Uses `PyJWT` + `cryptography` (added to requirements).
- `app/config.py` — added App settings (`GITHUB_APP_ID`, `GITHUB_APP_PRIVATE_KEY`, client id/secret,
  slug) + `github_app_enabled` + a `private_key_pem` helper that un-escapes `\n` (for single-line env
  UIs on hosting platforms).
- `app/services/github.py` — `_auth_token(installation_id)` now **prefers an App installation token
  and falls back to the PAT**. Every API function (`get_pr`, `get_diff`, `changed_files`,
  `fetch_file`, `post_comment`, `post_suggestion`, `set_status`) takes an optional `installation_id`.
  *Local/dev still works with just a PAT — nothing breaks.*
- `app/models.py` — `Review.installation_id` (the tenant marker).
- `app/services/review.py` + `app/services/tenants.py` *(new)* — `run_review` carries the
  installation through the whole pipeline; `on_installation()` records/suspends/removes installs.
- `app/api/webhooks.py` — now also handles `installation` / `installation_repositories` events and
  extracts `installation.id` from `pull_request` events.
- `app/db/store.py` — new `installations` table + `installation_id` column on reviews.
- `app/api/dashboard.py` — `GET /api/install` returns the public install URL for an "Install" button.
- `docs/GITHUB_APP_SETUP.md` *(new)* — **the click-through steps YOU do in GitHub's UI** to register
  the App (permissions, events, keys). This is the only manual part; once the keys are in `.env`,
  everything is automatic.

**What you need to do (one time):** follow `docs/GITHUB_APP_SETUP.md` to create the App and paste 5
values into `.env`. We can do this together when we deploy (Phase 5) since the webhook needs a public
URL.

**Tests added:** `test_github_falls_back_to_pat_when_no_app`, `test_tenant_installation_lifecycle`,
`test_review_persists_installation_id`. **24 tests passing.**

**Status after Phase 2:** CASARA is now *architecturally* a multi-tenant, installable product. Next
(Phase 3) we add real customer accounts + data isolation on Supabase, then deploy it live (Phase 5).

---

### Step 5 — Supabase multi-tenant store (Phase 3, data isolation)

**The problem it solves:** SQLite is one file on one server — fine for a demo, impossible for charging
many customers (no isolation, no hosted auth, no scaling). We move the data to **Supabase (Postgres)**
with **Row-Level Security** so each customer only sees their own data — without breaking local dev.

**The clever bit (so nothing breaks):** `app/db/store.py` is now a **dispatcher**. It picks the
backend at runtime: Supabase when `SUPABASE_URL` + `SUPABASE_SERVICE_KEY` are set, otherwise local
SQLite. Every caller still just writes `store.save_review(...)`. Tests stay on SQLite and stay green.

**Files touched:**
- `supabase/migrations/0001_init.sql` *(new)* — the Postgres schema: `installations` (the tenant),
  `reviews` (findings as `jsonb`), `usage_counters` (for Phase 4 billing). **RLS policies** let a
  logged-in user *read* only rows for installations they own; all *writes* go through the backend's
  service-role key (which bypasses RLS) — so the webhook pipeline isn't blocked but users are isolated.
- `app/db/sqlite_store.py` *(new)* — the original SQLite code, unchanged, now a backend.
- `app/db/supabase_store.py` *(new)* — same interface, talks to Supabase over PostgREST via httpx
  (no heavy SDK). Supports an optional `installation_id` filter for per-tenant lists/stats.
- `app/db/store.py` — rewritten as the runtime dispatcher.
- `app/config.py` — added `supabase_url` / `supabase_service_key` / `supabase_anon_key` + `use_supabase`.

**What you understand now:** "multi-tenant" = many customers, one app, data kept separate. We do it
with Postgres RLS (the database enforces isolation) rather than trusting application code to filter —
that's the safer, standard SaaS pattern.

> Still TODO in Phase 3 (needs your Supabase project to test against): the **GitHub OAuth login**
> flow and matching a logged-in user to their installations (`owner_user_id`). The schema + read
> policies are ready; the login wiring is the remaining piece.

---

### Step 6 — Deploy infrastructure + landing page (Phase 5, going live)

**The problem it solves:** Nothing earns money until it's *live* and a stranger can find, understand,
and install it. So: containerize the backend, blueprint the hosting, and build a real storefront.

**Files touched:**
- `backend/Dockerfile` *(new)* — Python 3.12 image; installs deps + Semgrep + Bandit so scanners work
  in production; runs uvicorn on Render's `$PORT`.
- `render.yaml` *(new)* — Render blueprint: one click provisions `casara-api`, with every secret as a
  `sync:false` env var (Render prompts you; real keys never get committed).
- `frontend/vercel.json` *(new)* — Vercel config for the Next.js frontend.
- `frontend/app/page.tsx` → **new marketing landing page** (the dashboard moved to
  `frontend/app/dashboard/page.tsx`). The landing page sells the product using the **real research
  numbers** (45% insecure AI code, 2.74× more issues in AI PRs, 28.6M secrets) and has "Install on
  GitHub" CTAs.
- `frontend/components/InstallButton.tsx` *(new)* — fetches the real App install URL from
  `GET /api/install` so the button works the moment the App is configured.
- `docs/DEPLOY.md` *(new)* — the full free-tier deploy runbook (Supabase → GitHub App → Render →
  Vercel → verify the whole loop).

**Verified:** frontend builds clean (`/` landing 11 kB, `/dashboard` works); backend 24 tests pass.

**Status after Phase 5 (code):** Everything that can be built *without your accounts* is built. The
product is live-ready: containerized backend, hosting blueprints, a selling landing page, and a
multi-tenant data layer. What's left is **plugging in your credentials and clicking deploy** — see the
final handoff checklist at the end of this session.

> Phase 4 (Stripe billing) is intentionally last — per your decision, we validate that people install
> and use it *before* building the paywall. The schema already has `usage_counters` + `plan` ready for it.

---

### Step 7 — Usage metering + free-tier cap (Phase 4, the billing data layer)

**The problem it solves:** To charge money you must (a) count what each customer uses and (b) be able
to cut off the free tier. We built both now — *without* Stripe — so the moment you add a Stripe
account, the paywall is a small final wire-up, not a rebuild.

**Files touched:**
- `app/db/*` — added `usage_counters` table + `incr_usage()` / `get_usage()` to both stores and the
  dispatcher. Counts reviews per installation per calendar month (`YYYY-MM`).
- `app/services/metering.py` *(new)* — `record_review()` (increment) and `over_free_limit()` (check
  against `FREE_MONTHLY_REVIEWS`).
- `app/services/review.py` — before any cost-incurring work, `run_review` checks the cap: if a free
  tenant is over limit it posts a friendly "upgrade to continue" comment and stops; otherwise it
  records one unit of usage and proceeds.
- `app/config.py` — `free_monthly_reviews` (default `0` = unlimited, so nothing is capped until you
  decide to meter).

**What's left for actual billing (the ONLY money step, needs your Stripe account):** a Stripe
checkout link + a webhook that flips an installation's `plan` from `free` to `pro` and lifts the cap.
That's ~1 file once you have Stripe keys. Everything it depends on (counters, plan column, cap check)
is already in place.

**Tests added:** `test_metering_counts_and_caps`. **25 tests passing.**

**Status: build complete for everything that doesn't need your credentials.** See the handoff
checklist (end of session / your chat) for the exact list of accounts and keys to plug in.

---

### Step 8 — Backend deployed live to Hugging Face Spaces (free, no card)

We deployed the backend to **Hugging Face Spaces** (Docker SDK) instead of Render — same Dockerfile,
free, and no credit card required.

- `backend/README.md` carries the HF Space metadata (`sdk: docker`, `app_port: 8000`), which also
  auto-converts a Gradio space to Docker on push.
- The backend folder was pushed to the Space `sharry121/CASARA` (secrets/venv/db excluded from the
  push — the Space repo is public, so only code goes there).
- All secrets live in the Space's **Settings → Secrets** (set in the HF dashboard + the private key
  added via the HF API so it never touched the chat/transcript).
- **Live URL:** `https://sharry121-casara.hf.space` — `/health` returns ok.

Remaining to go fully live: deploy the frontend (Vercel), then connect CORS + point the GitHub App
webhook at the HF URL and test a real PR.

---

### Step 9 — Competitive upgrade: custom rules, noise control, gating levels, agentic critic

Driven by deep market research (see `docs/ROADMAP.md`). Closes the table-stakes gaps every
competitor (CodeRabbit, Qodo, Semgrep) has, and adds the "advanced agentic" differentiator.

**`.casara.yml` per-repo config** (`app/core/config_file.py`, example at `.casara.example.yml`):
- Teams configure CASARA from their own repo (same pattern as CodeRabbit's `.coderabbit.yaml`).
- Supports: `languages` (scope analysis), per-path natural-language `rules`, `severity_overrides`
  (raise-only), `gate` level+threshold, `noise` (max_comments, min_confidence).
- Fetched from the PR head, validated with pydantic, falls back to safe defaults if absent/malformed.

**Custom per-path rules → AI agents:** matching rules' natural-language instructions are passed into
the security/logic/ai-code agent prompts so the AI enforces *your* team's policies.

**Language/framework scoping** (`_scope_by_language`): only files in the configured languages are
analysed; config/manifest files always pass through so secret + supply-chain checks still run.

**Noise control** (the #1 trust lever from the research — precision beats volume):
- `_filter_noise` drops AI findings below `min_confidence` (scanner-verified findings always kept).
- PR comment capped at `max_comments`, with a "+N more on the dashboard" footer.

**Gating levels** `off | warning | error`: warning surfaces risk without blocking; error blocks
(critical/verified-high still hard-gate under error); off never blocks.

**Agentic upgrade — orchestrated sub-agents + grounded critic loop:**
- The three specialized agents now run **in parallel** (ThreadPoolExecutor — they're I/O-bound LLM
  calls), cutting latency.
- A new **critic** (`analysis.critic`, `CRITIC_SYSTEM`) reviews the merged findings and drops/downgrades
  likely false positives — but **only among AI-only findings**, and grounded in the diff + scanner
  output (the research showed ungrounded reflection adds little). Scanner-verified findings are never
  dropped. This directly attacks the false-positive problem that hurts competitors.

**Tests:** +6 (config parse/defaults, glob matching, language scoping, severity overrides, noise
filter, keyless critic) → **31 passing**. Added `PyYAML` to requirements.

**Implements the user's three researched ideas:** (a) custom rules ✅, (b) advanced agentic
architecture ✅ (scoped: parallel + grounded critic), (c) language selection ✅.

---

### Step 10 — Tier 2 + full-stack alignment

**Declarative custom Semgrep rules (Tier 2 #5):** `.casara.yml` now supports `semgrep_config` — a
registry pack (`p/owasp-top-ten`) or a repo-relative rules dir/file. `scanners.run_semgrep` adds it as
a second `--config`, so teams get engine-enforced AST rules on top of the natural-language rules.

**Frontend ↔ backend alignment:** the dashboard now reflects every backend field:
- `lib/types.ts`: added `ai_signal` to `Finding` and `installation_id` to `Review`.
- `ReviewCard`: each finding now shows the 🤖 **AI signal** badge (why it looks AI-generated), a
  **confidence** indicator for unverified findings, and the existing verified badge — so the UI tells
  the full story the engine produces.

**Verified:** 32 backend tests pass; frontend builds clean (`/` + `/dashboard`).

**Deploy model recorded:** backend → push to the HF Space (Docker rebuild). Frontend → push to GitHub
`origin/main`, which Vercel auto-builds. Both done this step.

---

### Step 11 — Frontend redesign: "Operations Console / Threat Radar"

A full UI overhaul to an advanced, futuristic identity — **every widget backed by a real endpoint**
(no fake data). Followed a deliberate design plan, deliberately moving off the old cyan→emerald
gradient (a common AI look).

**Design system** (`tailwind.config.ts`, `app/globals.css`, `app/layout.tsx`):
- Palette: `ink #090c14` ground, `panel #141b2b` surface, **iris `#6d7bff`** brand accent (distinct
  from every status colour), and a separate **severity scale** (critical/high/medium/low/info) that
  encodes state in colour.
- Type: **Sora** (display) + **Inter** (UI) + **JetBrains Mono** (all data/metrics, tabular-nums) —
  three deliberate roles. Self-hosted via `next/font` (no CDN).
- Ambient: layered radar field + grid mask + a conic **radar-sweep** motion, all behind
  `prefers-reduced-motion`. Glass/panel surfaces, glow + tile shadows, skeleton shimmer, severity
  left-stripes, visible focus rings.

**Information design** (instrument primitives, `components/charts.tsx`):
- `RiskGauge` — SVG arc gauge for average risk (colour by level).
- `Sparkline` — risk trend across recent reviews (area + emphasised endpoint).
- `SeverityBar` — stacked threat-distribution bar with legend.
- All computed from the **real** `/api/reviews` + `/api/stats` data.

**Rebuilt components/pages:** `Header` (live SSE pulse + install), `MetricsPanel` (instrument tiles),
`ReviewCard` (severity-striped signal cards, findings grouped by severity, AI-signal chips, confidence,
fix preview), `FilterBar` (client-side search + blocked/passed tabs), `TriggerBar` (restyled),
`dashboard` (command-center layout + loading skeletons + empty states), `page` (radar-sweep hero with
the verified research stats). Removed the old flat `StatsBar`.

**Verified:** `next build` clean (`/` + `/dashboard`). Deployed via GitHub → Vercel.

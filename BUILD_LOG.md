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

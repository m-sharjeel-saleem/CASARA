<div align="center">

# 🧭 CASARA

### Contextual Automated Security Analysis & Risk Assessment

**Automated, scanner-grounded multi-agent security review for GitHub pull requests — with a composite risk score and automatic merge gating.**

`Python` · `FastAPI` · `LangGraph-style agents` · `Google Gemini` · `Semgrep` · `Bandit` · `Gitleaks` · `Next.js` · `SQLite`

</div>

---

## What it does

When a pull request is opened, CASARA:

1. **Verifies** the GitHub webhook (HMAC-SHA256) and processes it in the background.
2. **Scans** the changed files with deterministic tools — **Semgrep**, **Bandit**, **Gitleaks**.
3. **Grounds** two LLM agents (Security + Logic) in that scanner output to add context, explanations, and concrete fix prompts — while a guardrail treats the diff as untrusted (prompt-injection safe).
4. **Aggregates & cross-validates** — a finding confirmed by both a scanner and an agent is marked **verified**.
5. **Scores** the PR with a composite risk model (SAST · SCA · Secrets · Context) and **gates** the merge: it hard-blocks on any critical or verified-high finding via a GitHub commit status.
6. **Reports** a single consolidated review comment on the PR and streams everything live to the dashboard.

## Design philosophy: lean, not labyrinthine

This is the pragmatic, production-friendly build of the [CASARA research proposal](docs/CASARA_Research_Proposal.pdf) — deliberately built to **minimize internal moving parts**:

| Research proposal | This implementation | Why |
|---|---|---|
| Celery + Redis broker + pub/sub | FastAPI **background tasks** + in-process SSE | One process, no broker to operate |
| 5 scanners (incl. CodeQL) | **3 fast scanners** (Semgrep, Bandit, Gitleaks) | No compilation step; sub-minute scans |
| 6 agents | **2 agents + aggregator** | Lower cost, same grounding principle |
| Mandatory Postgres | **SQLite** (Postgres-ready) | Zero external DB to run locally |
| GitHub App + JWT | **Personal Access Token** | Simpler auth, fewer secrets |

Everything **degrades gracefully**: no Gemini key → scanner-only review; no scanners installed → agent-only; no GitHub token → dashboard-only. It always runs.

---

## Architecture

```
GitHub PR ─webhook─> FastAPI (HMAC verify) ─background task─┐
                                                             ▼
   ┌────────────── Review Orchestrator ──────────────────────────┐
   │  fetch changed files + diff                                  │
   │  Scanners:  Semgrep ‖ Bandit ‖ Gitleaks   (deterministic)    │
   │  Agents:    Security + Logic   (Gemini, grounded on scanners)│
   │  Aggregate → cross-validate → composite risk → gate decision │
   └──────────┬───────────────────────────────┬─────────────────┘
              ▼                                ▼
   GitHub: review comment + commit status   SQLite + in-process SSE → Next.js dashboard
```

## Composite risk score

```
R = 0.40·S_sast + 0.25·S_sca + 0.25·S_secrets + 0.10·S_context
```
Each dimension is driven by its most severe finding. The **gate** hard-blocks on any critical
or verified-high finding regardless of the blended score (see `app/core/risk.py`).

---

## Quickstart

```bash
# Backend (Python 3.12)
cd backend
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env          # add GEMINI_API_KEY, GITHUB_TOKEN, GITHUB_WEBHOOK_SECRET
uvicorn app.main:app --reload  # → http://localhost:8000/docs

# Optional scanners (the pipeline skips any that are missing)
pip install semgrep bandit && brew install gitleaks

# Frontend
cd ../frontend
npm install
cp .env.local.example .env.local
npm run dev                    # → http://localhost:3000
```

Connect a repo: add a GitHub webhook → Payload URL `https://<backend>/webhooks/github`,
content type `application/json`, secret = `GITHUB_WEBHOOK_SECRET`, event = *Pull requests*.
Or trigger manually from the dashboard with `owner/repo` + PR number.

## Project structure

```
backend/app/
  api/        webhooks (GitHub) · dashboard (reviews, stats, SSE, manual trigger)
  agents/     prompts · Security/Logic agents + aggregator/summary
  services/   scanners · github · llm (Gemini) · review (orchestrator)
  core/       security (HMAC + injection guard) · risk (score + gate) · events (SSE)
  db/         SQLite store
frontend/     Next.js dashboard (stats, live review feed, findings)
docs/         research proposal (PDF)
```

## Tests

```bash
cd backend && pytest -q     # 11 passing: risk, gating, aggregation, signatures, store
```

---

<div align="center">
Built by <b>M. Sharjeel Saleem</b> · <a href="https://github.com/m-sharjeel-saleem">GitHub</a>
</div>

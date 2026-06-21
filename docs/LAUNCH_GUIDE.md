# CASARA — Complete Launch Guide (every step, in detail)

This is the one document that takes CASARA from "code on your laptop" to "live product strangers can
install." Follow it **top to bottom**. Don't skip ahead — later steps need values from earlier ones.

There are **8 stages**. Rough time: ~60–90 minutes the first time.

```
0. Run it locally (prove it works)      ← optional but recommended
1. Push the code to GitHub
2. Get a Gemini API key
3. Create the Supabase project (database)
4. Create the GitHub App (makes it installable)
5. Deploy the backend to Render
6. Deploy the frontend to Vercel
7. Connect everything + test the full loop
8. (Later) Turn on billing with Stripe
```

A checklist of every secret you'll collect is at the very bottom — fill it in as you go.

---

## Stage 0 — Run it locally first (optional, ~10 min)

This proves the app works on your machine before you touch any cloud service. If you'd rather go
straight to deploying, skip to Stage 1.

### 0.1 Backend
```bash
cd /Users/muhammadsharjeel/Documents/Projects_old/CASARA/backend
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

Create your local secrets file from the template:
```bash
cp .env.example .env
```
Open `.env` and set **just one line** for now (leave everything else as-is):
```
GEMINI_API_KEY=<paste a real key from Stage 2 — or leave the placeholder to run keyless>
```
> With no real key, the app still runs — the AI agents just return nothing and the deterministic
> scanners + dependency checks do the work. Fine for a first smoke test.

Run it:
```bash
uvicorn app.main:app --reload
```
Open http://localhost:8000/health → you should see `{"status":"ok","version":"0.1.0"}`.
Leave this terminal running.

### 0.2 Frontend (second terminal)
```bash
cd /Users/muhammadsharjeel/Documents/Projects_old/CASARA/frontend
npm install
cp .env.local.example .env.local      # already points at http://localhost:8000
npm run dev
```
Open http://localhost:3000 → you should see the **landing page**.
Click **Dashboard** (top right) → http://localhost:3000/dashboard → the live dashboard.

✅ If both load, the app works. Stop the servers with `Ctrl+C` and continue to Stage 1.

---

## Stage 1 — Push the code to GitHub (~5 min)

Your repo already exists at **https://github.com/m-sharjeel-saleem/CASARA** with the original commit.
All the new work is on a branch called `phase-1-ai-guardrail`. We'll push that branch, then merge it
into `main` so `main` has the full product (Render/Vercel deploy from `main` by default).

```bash
cd /Users/muhammadsharjeel/Documents/Projects_old/CASARA

# 1. Push the feature branch (backs your work up immediately)
git push -u origin phase-1-ai-guardrail
```

Now bring it into `main`:
```bash
git checkout main
git merge phase-1-ai-guardrail
git push origin main
```

> **If `git push` asks for a password:** GitHub no longer accepts your account password on the
> command line. Use a **Personal Access Token** as the password:
> 1. Go to https://github.com/settings/tokens → **Generate new token (classic)**.
> 2. Scope: tick **repo**. Generate. Copy the `ghp_…` token.
> 3. When git prompts for username, enter your GitHub username; for password, paste the token.
> (macOS will remember it in Keychain after the first time.)

✅ Refresh https://github.com/m-sharjeel-saleem/CASARA — you should see all the new folders
(`backend/app/agents/autofix.py`, `supabase/`, `docs/`, `render.yaml`, the landing page, etc.).

---

## Stage 2 — Get a Gemini API key (~3 min)

This is the brain of the AI agents.

1. Go to **https://aistudio.google.com/apikey** and sign in with your Google account.
2. Click **Create API key** → **Create API key in new project** (or pick a project).
3. Copy the key (starts with `AIza…`).
4. **Save it** — it goes in the checklist as `GEMINI_API_KEY`.

> Keep this private. It's billed to your Google account (there's a free tier; CASARA's per-PR usage
> is small and capped by `MAX_AUTOFIXES`).

---

## Stage 3 — Create the Supabase project (the database) (~10 min)

Supabase gives you a hosted Postgres database with per-customer data isolation.

### 3.1 Create the project
1. Go to **https://supabase.com** → sign in (use "Continue with GitHub" — easiest).
2. Click **New project**.
   - **Name:** `casara`
   - **Database Password:** click **Generate a password**, then **copy and save it** (you may need
     it later; not required for CASARA's setup, but don't lose it).
   - **Region:** pick the one closest to you.
3. Click **Create new project**. Wait ~2 minutes for it to provision.

### 3.2 Create the tables
1. In the left sidebar, click **SQL Editor**.
2. Click **+ New query**.
3. Open the file `supabase/migrations/0001_init.sql` from this repo, copy **all** of it, paste into
   the editor.
4. Click **Run** (bottom right). You should see "Success. No rows returned."
   - This creates 3 tables (`installations`, `reviews`, `usage_counters`) and the security rules.
5. Verify: left sidebar → **Table Editor** → you should see the 3 tables.

### 3.3 Copy the keys
1. Left sidebar → **Project Settings** (gear icon) → **API**.
2. Copy these three values into your checklist:
   - **Project URL** → `SUPABASE_URL`  (looks like `https://abcxyz.supabase.co`)
   - Under **Project API keys**: **`service_role`** (click "reveal") → `SUPABASE_SERVICE_KEY`
     ⚠️ This is a secret — it bypasses all security rules. Never put it in the frontend or commit it.
   - **`anon` `public`** → `SUPABASE_ANON_KEY`

✅ Database ready.

---

## Stage 4 — Create the GitHub App (makes it installable) (~15 min)

This is the step that turns CASARA into a product people can click "Install" on. It's all clicks in
GitHub's settings. (There's a shorter version in `docs/GITHUB_APP_SETUP.md`; this is the detailed one.)

> **Heads up:** the App needs a **public Webhook URL**. You don't have one until the backend is
> deployed (Stage 5). Two options:
> - **(Recommended)** Put a *placeholder* URL now (e.g. `https://example.com/webhooks/github`),
>   finish Stage 5 to get your real Render URL, then come back and update the webhook URL.
> - Or use a temporary tunnel (`smee.io`) — only needed if you want to test webhooks before deploying.
>
> We'll use the recommended path: placeholder now, real URL after Stage 5.

### 4.1 Register the App
1. Go to **https://github.com/settings/apps** → **New GitHub App**.
   (Or for an org: Org → Settings → Developer settings → GitHub Apps → New GitHub App.)
2. Fill in:
   - **GitHub App name:** `CASARA Security <yourname>` (must be globally unique — add your name).
   - **Homepage URL:** `https://github.com/m-sharjeel-saleem/CASARA` (your repo for now).
   - **Webhook → Active:** ✅ leave checked.
   - **Webhook URL:** `https://example.com/webhooks/github` (placeholder — we fix this in Stage 7).
   - **Webhook secret:** open a terminal and run `openssl rand -hex 32`, copy the output. Paste it
     here **and save it** as `GITHUB_WEBHOOK_SECRET` in your checklist.

### 4.2 Set permissions (least privilege — only what CASARA uses)
Scroll to **Repository permissions** and set:
| Permission | Set to | Why |
|---|---|---|
| **Contents** | Read-only | read the changed files to scan them |
| **Pull requests** | Read and write | post the review comment + suggested fixes |
| **Commit statuses** | Read and write | set the pass/block gate on the PR |
| **Metadata** | Read-only | (auto-selected, mandatory) |

Leave everything else as "No access."

### 4.3 Subscribe to events
Scroll to **Subscribe to events** and tick:
- ✅ **Pull request**
- ✅ **Installation**
- ✅ **Installation repositories**

### 4.4 Who can install it
Under **Where can this GitHub App be installed?** choose **Any account**
(so other people — your future customers — can install it).

### 4.5 Create + collect credentials
1. Click **Create GitHub App**.
2. On the App's page, collect into your checklist:
   - **App ID** (near the top) → `GITHUB_APP_ID`
   - **Client ID** → `GITHUB_APP_CLIENT_ID`
   - Click **Generate a new client secret** → copy → `GITHUB_APP_CLIENT_SECRET`
   - The **public slug** is in the URL `https://github.com/apps/<slug>` (or "Public link"
     on the page) → `GITHUB_APP_SLUG`
   - Scroll to **Private keys** → **Generate a private key**. A `.pem` file downloads.
     Open it in a text editor; you'll paste its **entire contents** into `GITHUB_APP_PRIVATE_KEY`
     in Stage 5 (Render handles multi-line values, so paste it as-is there).

✅ GitHub App created. We'll point its webhook at the real backend in Stage 7.

---

## Stage 5 — Deploy the backend to Render (~15 min)

Render runs your FastAPI backend. The repo has a `render.yaml` blueprint that sets it all up.

1. Go to **https://render.com** → sign up / sign in (use "GitHub" to connect your account).
2. If asked, **authorize Render to access** your `CASARA` repo (you can limit it to that one repo).
3. Click **New +** (top right) → **Blueprint**.
4. Select the **`m-sharjeel-saleem/CASARA`** repo → **Connect**.
5. Render reads `render.yaml` and shows a service named **`casara-api`**. Click **Apply** / **Create**.
6. Render now asks you to fill the secret env vars (the ones marked `sync:false`). Paste each from
   your checklist:
   | Env var | Value |
   |---|---|
   | `GEMINI_API_KEY` | your Gemini key (Stage 2) |
   | `GITHUB_APP_ID` | from Stage 4.5 |
   | `GITHUB_APP_SLUG` | from Stage 4.5 |
   | `GITHUB_APP_CLIENT_ID` | from Stage 4.5 |
   | `GITHUB_APP_CLIENT_SECRET` | from Stage 4.5 |
   | `GITHUB_APP_PRIVATE_KEY` | paste the **whole** `.pem` file contents |
   | `GITHUB_WEBHOOK_SECRET` | from Stage 4.1 |
   | `SUPABASE_URL` | from Stage 3.3 |
   | `SUPABASE_SERVICE_KEY` | from Stage 3.3 |
   | `SUPABASE_ANON_KEY` | from Stage 3.3 |
   | `CORS_ORIGINS` | leave blank for now — we set it in Stage 7 after Vercel |
7. Click **Create / Deploy**. Watch the logs; first build takes ~3–5 min (it installs the scanners).
8. When it says **Live**, copy your backend URL — it looks like
   **`https://casara-api.onrender.com`** (yours may have a suffix). Save it as `BACKEND_URL`.
9. Test it: open **`https://<your-backend>.onrender.com/health`** → `{"status":"ok",...}`.

> ⚠️ **Free Render services sleep after ~15 min idle.** The first request after sleeping takes ~30s
> to wake. That's fine for a demo; upgrade to a paid plan later if you need it always-on.

✅ Backend live.

---

## Stage 6 — Deploy the frontend to Vercel (~10 min)

Vercel hosts your Next.js landing page + dashboard.

1. Go to **https://vercel.com** → sign in with **GitHub**.
2. Click **Add New… → Project**.
3. Find **`m-sharjeel-saleem/CASARA`** → **Import**.
4. **IMPORTANT — set the Root Directory:**
   - Click **Edit** next to "Root Directory" → select the **`frontend`** folder → **Continue**.
   - (Without this, Vercel tries to build the whole repo and fails.)
5. **Framework Preset** should auto-detect **Next.js**. Leave build settings default.
6. Expand **Environment Variables** and add one:
   - **Name:** `NEXT_PUBLIC_API_URL`
   - **Value:** your `BACKEND_URL` from Stage 5.8 (e.g. `https://casara-api.onrender.com`)
7. Click **Deploy**. Wait ~2 min.
8. Copy your frontend URL — e.g. **`https://casara.vercel.app`**. Save it as `FRONTEND_URL`.

✅ Frontend live. Visit `FRONTEND_URL` → the landing page should load.

---

## Stage 7 — Connect everything + test the full loop (~10 min)

Three small connections, then a real end-to-end test.

### 7.1 Tell the backend to trust the frontend (CORS)
1. Render → your `casara-api` service → **Environment** tab.
2. Set **`CORS_ORIGINS`** = your `FRONTEND_URL` (e.g. `https://casara.vercel.app`).
3. **Save** → Render redeploys automatically (~1 min).

### 7.2 Point the GitHub App webhook at the real backend
1. Go to **https://github.com/settings/apps** → your CASARA app → **General** (or **Webhook**).
2. Set **Webhook URL** = `https://<your-backend>.onrender.com/webhooks/github`.
3. **Save changes.**

### 7.3 Install the App on a test repo
1. On the App page, click **Install App** (left sidebar) → choose your account → pick **one test repo**
   (make a throwaway repo if needed) → **Install**.
2. This fires an `installation` webhook → CASARA records your tenant in Supabase
   (check Supabase → Table Editor → `installations` → you should see a row).

### 7.4 Trigger a real review
1. In the test repo, create a file with an obvious problem, e.g. `vuln.py`:
   ```python
   import sqlite3
   def get_user(db, name):
       # insecure: string-built SQL (the AI-code agent should catch this)
       return db.execute("SELECT * FROM users WHERE name = '" + name + "'").fetchone()

   PASSWORD = "supersecret123"   # hardcoded secret
   ```
2. Commit it on a **new branch** and open a **Pull Request** into `main`.
3. Within ~30–60s (longer if Render was asleep), on the PR you should see:
   - A **CASARA Security Review** comment with a risk score + findings table (with an 🤖 AI-signal).
   - A **suggested fix** comment with an "Apply suggestion" button.
   - A **status check** named `casara/security-review` (pass/blocked).
4. Open your `FRONTEND_URL/dashboard` → the review appears there too.

### 7.5 (Recommended) Make the gate actually block merges
1. Test repo → **Settings → Branches → Add branch protection rule**.
2. **Branch name pattern:** `main`.
3. Tick **Require status checks to pass before merging** → search and select
   **`casara/security-review`**.
4. Save. Now a PR with a critical finding **cannot be merged** until it's clean.

✅ **You now have a live, installable, multi-tenant AI security product.** 🎉

---

## Stage 8 — (Later) Turn on billing with Stripe

Do this **only once people are installing and using it** (your decision: validate first). When ready:
1. Create a **Stripe account** → get your API keys (test mode first).
2. Tell me "let's add Stripe" — I'll add the checkout link + webhook (one small file) that flips an
   installation's `plan` from `free` to `pro` and lifts the usage cap.
3. To start metering the free tier before that, set `FREE_MONTHLY_REVIEWS` on Render to e.g. `50`.
   (Default `0` = unlimited, so nothing is capped until you choose to.)

---

## 📋 Secrets checklist (fill in as you go)

| Key | Where it's from | Your value |
|---|---|---|
| `GEMINI_API_KEY` | Stage 2 | |
| `SUPABASE_URL` | Stage 3.3 | |
| `SUPABASE_SERVICE_KEY` | Stage 3.3 | |
| `SUPABASE_ANON_KEY` | Stage 3.3 | |
| `GITHUB_APP_ID` | Stage 4.5 | |
| `GITHUB_APP_SLUG` | Stage 4.5 | |
| `GITHUB_APP_CLIENT_ID` | Stage 4.5 | |
| `GITHUB_APP_CLIENT_SECRET` | Stage 4.5 | |
| `GITHUB_APP_PRIVATE_KEY` | Stage 4.5 (.pem file) | |
| `GITHUB_WEBHOOK_SECRET` | Stage 4.1 | |
| `BACKEND_URL` (Render) | Stage 5.8 | |
| `FRONTEND_URL` (Vercel) | Stage 6.8 | |

> ⚠️ Never commit these to git. They live only in Render (backend) and Vercel (frontend) dashboards,
> and in your local `backend/.env` (which is git-ignored).

---

## Troubleshooting

- **`/health` works but the PR gets no comment:** check the GitHub App webhook URL (Stage 7.2) and
  that you installed the App on that repo (Stage 7.3). On the App page → **Advanced** → "Recent
  Deliveries" shows each webhook and the response — a 401 means the webhook secret doesn't match.
- **Frontend shows "Cannot reach the CASARA API":** `NEXT_PUBLIC_API_URL` (Vercel) must equal your
  Render URL, and `CORS_ORIGINS` (Render) must equal your Vercel URL. Both must be exact (https, no
  trailing slash).
- **First review is very slow:** the free Render service was asleep; it wakes in ~30s. Subsequent
  reviews are fast.
- **Reviews appear but no findings:** confirm `GEMINI_API_KEY` is set on Render; without it only the
  deterministic scanners run.
- **Vercel build fails:** you probably missed setting **Root Directory = `frontend`** (Stage 6.4).
```

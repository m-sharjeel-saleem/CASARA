# Deploying CASARA (free tier: Render + Vercel + Supabase)

This gets CASARA **live and installable**. Order matters — do these top to bottom. Everything here
needs *your* accounts and keys; the code is already wired for all of it.

## 0. What you'll need (free accounts)
- A Gemini API key — https://aistudio.google.com/apikey
- GitHub account (to create the App)
- Render account (backend) — https://render.com
- Vercel account (frontend) — https://vercel.com
- Supabase account (database + auth) — https://supabase.com

---

## 1. Supabase (the database)
1. Create a new project. Wait for it to provision.
2. Open **SQL Editor**, paste the contents of `supabase/migrations/0001_init.sql`, run it.
3. **Project Settings → API**, copy:
   - **Project URL** → `SUPABASE_URL`
   - **service_role** secret key → `SUPABASE_SERVICE_KEY` (⚠️ server-side only, never in frontend)
   - **anon public** key → `SUPABASE_ANON_KEY`

## 2. GitHub App
Follow **`docs/GITHUB_APP_SETUP.md`** completely. You'll set the webhook URL to your Render URL —
so you can either deploy the backend first and come back, or use a temporary `smee.io` URL now and
update it after step 3. Collect the 5 App values + the webhook secret.

## 3. Backend → Render
1. Push this repo to GitHub (see "Pushing" below).
2. Render → **New + → Blueprint**, pick this repo. It reads `render.yaml` and creates `casara-api`.
3. When prompted, fill the `sync:false` env vars: the Gemini key, all `GITHUB_APP_*` values, the
   webhook secret, the three `SUPABASE_*` values, and `CORS_ORIGINS` (your Vercel URL, added in step 4).
4. Deploy. Confirm `https://<your-service>.onrender.com/health` returns `{"status":"ok"}`.
5. Go back to the GitHub App settings and set the **Webhook URL** to
   `https://<your-service>.onrender.com/webhooks/github`.

> Free Render services sleep after inactivity; the first webhook after idle may take ~30s to wake.

## 4. Frontend → Vercel
1. Vercel → **Add New → Project**, import this repo, set **Root Directory = `frontend`**.
2. Env var: `NEXT_PUBLIC_API_URL = https://<your-service>.onrender.com`
3. Deploy. Copy the Vercel URL and add it to the backend's `CORS_ORIGINS` on Render (redeploy backend).

## 5. Verify the whole loop
1. Visit your Vercel URL → landing page → **Install on GitHub** → install on a test repo.
2. Open a PR on that repo with an obvious issue (e.g. `password == "admin"` or a `postinstall` script).
3. Within ~a minute: CASARA posts a review comment, sets the `casara/security-review` status, and (if
   fixable) posts a suggested fix. The review appears on `/dashboard`.

---

## Pushing the repo
```bash
git push -u origin phase-1-ai-guardrail      # or merge to main first
```

## Cost
All four services have free tiers sufficient to launch and demo. The only metered cost is Gemini
API usage, bounded by `MAX_AUTOFIXES` and the per-PR agent calls. Add a paid plan only once you have
real usage (Phase 4 / Stripe).

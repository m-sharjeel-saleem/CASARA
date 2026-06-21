# Creating the CASARA GitHub App

This is the **one-time, click-through setup you do in GitHub's UI**. It turns CASARA from a
single-user PAT tool into a product that any org can click "Install" on. After this, the backend
authenticates *as each installation* automatically (code in `app/services/gh_app.py`).

> You don't need a deployed server to create the App. But the webhook needs a public URL — use your
> Render URL once deployed (Phase 5), or a temporary `ngrok`/`smee.io` URL for local testing.

## 1. Register the App

1. Go to **https://github.com/settings/apps/new** (or Org settings → Developer settings → GitHub Apps).
2. **GitHub App name:** `CASARA Security` (must be globally unique; the slug is derived from it).
3. **Homepage URL:** your landing page (or the repo for now).
4. **Webhook → Active:** ✅ checked.
   - **Webhook URL:** `https://<your-backend-host>/webhooks/github`
   - **Webhook secret:** generate a long random string. **Save it** — it goes in `GITHUB_WEBHOOK_SECRET`.
5. **Repository permissions** (least privilege — only what CASARA uses):
   | Permission | Access | Why |
   |---|---|---|
   | Contents | Read-only | fetch changed file contents to scan |
   | Pull requests | Read & write | post the review comment + suggested fixes |
   | Commit statuses | Read & write | set the pass/block gate on the PR |
   | Metadata | Read-only | (mandatory, auto-selected) |
6. **Subscribe to events:** `Pull request`, `Installation`, `Installation repositories`.
7. **Where can this App be installed?** "Any account" (so other people can install it = customers).
8. Click **Create GitHub App**.

## 2. Collect the credentials → put them in `backend/.env`

After creating, on the App's settings page:
- **App ID** (top of page) → `GITHUB_APP_ID`
- **Client ID** → `GITHUB_APP_CLIENT_ID`
- **Generate a client secret** → `GITHUB_APP_CLIENT_SECRET`
- The **public slug** in the App's URL `github.com/apps/<slug>` → `GITHUB_APP_SLUG`
- **Generate a private key** (bottom) → downloads a `.pem`. Open it and paste the full contents into
  `GITHUB_APP_PRIVATE_KEY`. If your host's env UI is single-line, replace each real newline with `\n`
  (the code converts `\n` back to newlines for you).

## 3. Test it

1. Start the backend, then click **Install App** on the App page and install it on a test repo.
   - GitHub fires an `installation` webhook → CASARA records the tenant (`installations` table).
2. Open a pull request on that repo.
   - GitHub fires a `pull_request` webhook with `installation.id` → CASARA reviews the PR **as that
     installation** (no PAT needed) and posts the comment + status + any suggested fixes.

## 4. Make the gate enforce merges (optional but recommended)

In the test repo: **Settings → Branches → Add branch protection rule** for `main` →
**Require status checks to pass** → select `casara/security-review`. Now a blocked PR cannot be merged.

---

**That's the whole "installable product" step.** Once the App vars are in `.env`, the backend
prefers App auth automatically and falls back to the PAT only if they're empty — so local dev still
works with just a PAT.

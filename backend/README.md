---
title: CASARA API
emoji: 🛡️
colorFrom: indigo
colorTo: purple
sdk: docker
app_port: 8000
pinned: false
---

# CASARA API (backend)

FastAPI backend for CASARA — an AI-code security guardrail for GitHub pull requests.
This Space hosts the API: it receives GitHub webhooks, runs the scanner + AI-agent review
pipeline, scores risk, gates merges, and posts suggested fixes.

- Health check: `/health`
- GitHub webhook: `/webhooks/github`
- Dashboard API: `/api/*`

Configuration is provided via **Space secrets** (Settings → Variables and secrets), never in code.
See `../docs/LAUNCH_GUIDE.md` for full setup.

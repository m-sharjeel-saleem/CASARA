# CASARA backend — FastAPI + scanners. Deploys to Render (or any container host).
FROM python:3.12-slim

ENV PYTHONUNBUFFERED=1 PIP_NO_CACHE_DIR=1

WORKDIR /app

# git is needed by some scanners; build-essential for any wheels without prebuilts.
RUN apt-get update && apt-get install -y --no-install-recommends git \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install -r requirements.txt
# Deterministic scanners (pure-pip). Gitleaks is an optional extra binary; depscan
# (our supply-chain check) is pure-Python and always runs.
RUN pip install semgrep==1.97.0 bandit==1.8.0

COPY app ./app

EXPOSE 8000
# Render provides $PORT; default to 8000 locally.
CMD ["sh", "-c", "uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8000}"]

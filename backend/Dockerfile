# CASARA backend — FastAPI + scanners. Deploys to Render (or any container host).
FROM python:3.12-slim

ENV PYTHONUNBUFFERED=1 PIP_NO_CACHE_DIR=1

WORKDIR /app

# git is needed by some scanners; build-essential for any wheels without prebuilts.
RUN apt-get update && apt-get install -y --no-install-recommends git curl ca-certificates \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install -r requirements.txt
# Deterministic scanners. Pure-pip: Semgrep (SAST), Bandit (Python), GuardDog (malware/
# malicious-package detection). depscan (our supply-chain heuristics) is pure-Python.
RUN pip install semgrep==1.97.0 bandit==1.8.0 guarddog==1.8.0

# Single-binary scanners for the whole-repo audit: OSV-Scanner (dependency vulns from 20+
# advisory sources) and Trivy (misconfig/IaC + secrets). Installed to /usr/local/bin.
RUN ARCH=$(dpkg --print-architecture) \
    && curl -sSfL "https://github.com/google/osv-scanner/releases/download/v2.0.2/osv-scanner_linux_${ARCH}" \
       -o /usr/local/bin/osv-scanner && chmod +x /usr/local/bin/osv-scanner \
    && curl -sSfL https://raw.githubusercontent.com/aquasecurity/trivy/main/contrib/install.sh \
       | sh -s -- -b /usr/local/bin v0.58.1 \
    || echo "scanner binary install best-effort; pipeline degrades gracefully if absent"

COPY app ./app

EXPOSE 8000
# Render provides $PORT; default to 8000 locally.
CMD ["sh", "-c", "uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8000}"]

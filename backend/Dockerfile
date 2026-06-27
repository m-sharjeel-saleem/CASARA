# CASARA backend — FastAPI + scanners. Deploys to Render (or any container host).
FROM python:3.12-slim

ENV PYTHONUNBUFFERED=1 PIP_NO_CACHE_DIR=1

WORKDIR /app

# git is needed by some scanners; build-essential for any wheels without prebuilts.
RUN apt-get update && apt-get install -y --no-install-recommends git curl ca-certificates \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install -r requirements.txt
# Deterministic scanners (main env): Semgrep (SAST) + Bandit (Python).
RUN pip install semgrep==1.97.0 bandit==1.8.0

# GuardDog (malware / malicious-package detection) pins an older semgrep, so install it in an
# ISOLATED venv and expose just its CLI — avoids clashing with the app's semgrep 1.97.
RUN python -m venv /opt/guarddog \
    && /opt/guarddog/bin/pip install --no-cache-dir guarddog==1.8.0 \
    && ln -s /opt/guarddog/bin/guarddog /usr/local/bin/guarddog \
    || echo "guarddog install best-effort; pipeline degrades gracefully if absent"

# Single-binary scanners for the whole-repo audit: OSV-Scanner (dependency vulns) and Trivy
# (misconfig/IaC + secrets). Direct binary downloads to /usr/local/bin (best-effort).
RUN ARCH=$(dpkg --print-architecture) \
    && curl -sSfL "https://github.com/google/osv-scanner/releases/download/v2.0.2/osv-scanner_linux_${ARCH}" \
       -o /usr/local/bin/osv-scanner && chmod +x /usr/local/bin/osv-scanner \
    || echo "osv-scanner install best-effort"
RUN ARCH=$(dpkg --print-architecture) \
    && TARCH=$( [ "$ARCH" = "arm64" ] && echo "Linux-ARM64" || echo "Linux-64bit" ) \
    && curl -sSfL "https://github.com/aquasecurity/trivy/releases/download/v0.58.1/trivy_0.58.1_${TARCH}.tar.gz" \
       -o /tmp/trivy.tgz \
    && tar -xzf /tmp/trivy.tgz -C /usr/local/bin trivy && chmod +x /usr/local/bin/trivy \
    && rm -f /tmp/trivy.tgz \
    || echo "trivy install best-effort; pipeline degrades gracefully if absent"

COPY app ./app

EXPOSE 8000
# Render provides $PORT; default to 8000 locally.
CMD ["sh", "-c", "uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8000}"]

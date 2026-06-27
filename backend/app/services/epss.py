"""EPSS enrichment — real-world exploit-probability for CVE findings.

EPSS (Exploit Prediction Scoring System, FIRST.org) gives each CVE a 0–1 probability of
exploitation in the next 30 days. We attach it to any finding whose id is a CVE (mainly from
OSV-Scanner) so triage/prioritisation is grounded in live exploit data, not just severity.
Free API, no key. Degrades silently on failure (the field stays 0.0).
"""
import logging
import re

import httpx

from app.models import Finding

log = logging.getLogger("casara.epss")
_CVE = re.compile(r"CVE-\d{4}-\d{4,}", re.IGNORECASE)
_API = "https://api.first.org/data/v1/epss"


def enrich(findings: list[Finding]) -> None:
    """Attach EPSS scores in-place to findings that carry a CVE id (batched, one request)."""
    cves = sorted({m.group(0).upper() for f in findings
                   if (m := _CVE.search(f.cwe_id or ""))})
    if not cves:
        return
    try:
        with httpx.Client(timeout=20) as c:
            r = c.get(_API, params={"cve": ",".join(cves[:100])})
            r.raise_for_status()
            scores = {d["cve"].upper(): float(d.get("epss", 0.0)) for d in r.json().get("data", [])}
    except (httpx.HTTPError, ValueError, KeyError) as e:
        log.info("EPSS enrichment skipped: %s", e)
        return
    for f in findings:
        m = _CVE.search(f.cwe_id or "")
        if m:
            f.epss = scores.get(m.group(0).upper(), 0.0)
    log.info("EPSS enriched %d CVE finding(s)", len(cves))

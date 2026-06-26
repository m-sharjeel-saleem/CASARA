"""Per-repo configuration: `.casara.yml`.

Lets a team customise CASARA without touching the service — the same pattern CodeRabbit
(`.coderabbit.yaml`) and Qodo (`best_practices.md`) use. Fetched from the PR head, parsed,
validated, and falls back to safe defaults when absent or malformed.

Example `.casara.yml`:

    version: 1
    languages: [python, javascript]      # scope analysis; empty = all
    gate:
      level: error                        # off | warning | error
      threshold: 7.0
    noise:
      max_comments: 10
      min_confidence: MEDIUM              # drop findings below this confidence
    rules:
      - path: "src/auth/**"
        instructions: "Auth code — be strict about session handling and authz checks."
        severity: high
      - path: "**/*.py"
        instructions: "Require parameterized SQL; flag eval()/exec()."
    severity_overrides:
      CWE-89: critical
"""
from __future__ import annotations

import fnmatch
import logging

import yaml
from pydantic import BaseModel, Field, ValidationError

from app.models import Confidence, Severity

log = logging.getLogger("casara.config_file")

CONFIG_PATHS = (".casara.yml", ".casara.yaml")


class PathRule(BaseModel):
    path: str                                  # glob, e.g. "src/auth/**" or "**/*.py"
    instructions: str = ""                     # natural-language guidance for the AI agents
    severity: Severity | None = None           # optional severity floor for matches


class GateCfg(BaseModel):
    level: str = "error"                       # off | warning | error
    threshold: float = 7.0


class NoiseCfg(BaseModel):
    max_comments: int = 10                     # cap inline findings shown per PR
    min_confidence: Confidence = "LOW"         # drop findings below this confidence


class CasaraConfig(BaseModel):
    version: int = 1
    languages: list[str] = Field(default_factory=list)
    rules: list[PathRule] = Field(default_factory=list)
    gate: GateCfg = Field(default_factory=GateCfg)
    noise: NoiseCfg = Field(default_factory=NoiseCfg)
    severity_overrides: dict[str, Severity] = Field(default_factory=dict)
    # Extra Semgrep ruleset to enforce, e.g. a registry pack ("p/owasp-top-ten") or a
    # repo-relative rules dir/file ("ci/semgrep-rules/"). Declarative AST rules, engine-enforced.
    semgrep_config: str = ""

    def instructions_for(self, files: list[str]) -> str:
        """Concatenated natural-language rules whose glob matches any changed file."""
        out: list[str] = []
        for rule in self.rules:
            if rule.instructions and any(_match(f, rule.path) for f in files):
                out.append(f"- ({rule.path}) {rule.instructions}")
        return "\n".join(out)


def _match(path: str, pattern: str) -> bool:
    # Support "**/" style globs reasonably via fnmatch on the full path.
    return fnmatch.fnmatch(path, pattern) or fnmatch.fnmatch(path, pattern.replace("**/", "*"))


_DEFAULT = CasaraConfig()


def _yaml_dict(text: str | None) -> dict:
    if not text:
        return {}
    try:
        data = yaml.safe_load(text)
        return data if isinstance(data, dict) else {}
    except yaml.YAMLError as e:
        log.warning("invalid YAML config: %s", e)
        return {}


def _merge(base: dict, over: dict) -> dict:
    """Greptile-style merge: `over` (repo file) wins; rules/overrides are combined."""
    out = dict(base)
    for k, v in over.items():
        if k == "rules" and isinstance(v, list) and isinstance(base.get("rules"), list):
            out["rules"] = base["rules"] + v
        elif k == "severity_overrides" and isinstance(v, dict) and isinstance(base.get(k), dict):
            out["severity_overrides"] = {**base[k], **v}
        else:
            out[k] = v
    return out


def _build(data: dict) -> CasaraConfig:
    try:
        return CasaraConfig(**data)
    except (ValidationError, TypeError) as e:
        log.warning("invalid merged config, using defaults: %s", e)
        return _DEFAULT


def parse_config(text: str | None) -> CasaraConfig:
    """Parse YAML text into a validated config; return defaults on any problem."""
    data = _yaml_dict(text)
    return _build(data) if data else _DEFAULT


def load_config(repo: str, ref: str, installation_id: int | None = None) -> CasaraConfig:
    """Effective config = dashboard org defaults (Supabase) merged UNDER the repo's
    `.casara.yml` (repo file wins). Lets teams configure rules from the web OR the repo."""
    from app.services import github

    dashboard: dict = {}
    if installation_id:
        try:
            from app.db import store
            dashboard = store.get_config(installation_id) or {}
        except Exception as e:  # noqa: BLE001 — never let config read break a review
            log.warning("dashboard config read failed: %s", e)

    repo_cfg: dict = {}
    for path in CONFIG_PATHS:
        text = github.fetch_file(repo, path, ref, installation_id)
        if text is not None:
            repo_cfg = _yaml_dict(text)
            break

    if not dashboard and not repo_cfg:
        return _DEFAULT
    return _build(_merge(dashboard, repo_cfg))

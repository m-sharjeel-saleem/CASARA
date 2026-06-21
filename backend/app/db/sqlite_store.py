"""SQLite persistence — zero external connections.

Findings are stored as a JSON column on the review row, so a review is a single
record with no joins. This keeps the data layer deliberately simple (the
"fewer internal connections" design goal).
"""
import json
import sqlite3
from contextlib import contextmanager

from app.config import get_settings
from app.models import Review

_SCHEMA = """
create table if not exists reviews (
    id              text primary key,
    repo            text not null,
    pr_number       integer not null,
    installation_id integer,
    pr_title        text,
    author          text,
    head_sha        text,
    status          text,
    risk_score      real,
    gated           integer,
    summary         text,
    findings_json   text,
    created_at      text,
    completed_at    text
);
create index if not exists reviews_repo_idx on reviews (repo);
create index if not exists reviews_created_idx on reviews (created_at desc);

-- One row per GitHub App installation (the tenant boundary until Supabase takes over).
create table if not exists installations (
    id           integer primary key,
    account      text,
    account_type text,
    repo_count   integer,
    created_at   text,
    suspended    integer default 0
);
"""


@contextmanager
def _conn():
    con = sqlite3.connect(get_settings().database_path)
    con.row_factory = sqlite3.Row
    try:
        yield con
        con.commit()
    finally:
        con.close()


def init_db() -> None:
    with _conn() as con:
        con.executescript(_SCHEMA)


def save_review(review: Review) -> None:
    with _conn() as con:
        con.execute(
            """insert into reviews
               (id, repo, pr_number, installation_id, pr_title, author, head_sha, status,
                risk_score, gated, summary, findings_json, created_at, completed_at)
               values (?,?,?,?,?,?,?,?,?,?,?,?,?,?)
               on conflict(id) do update set
                 status=excluded.status, risk_score=excluded.risk_score,
                 gated=excluded.gated, summary=excluded.summary,
                 findings_json=excluded.findings_json, completed_at=excluded.completed_at""",
            (
                review.id, review.repo, review.pr_number, review.installation_id,
                review.pr_title, review.author, review.head_sha, review.status,
                review.risk_score, int(review.gated),
                review.summary, json.dumps([f.model_dump() for f in review.findings]),
                review.created_at, review.completed_at,
            ),
        )


def _row_to_review(row: sqlite3.Row) -> Review:
    data = dict(row)
    findings = json.loads(data.pop("findings_json") or "[]")
    data["gated"] = bool(data["gated"])
    return Review(**data, findings=findings)


def get_review(review_id: str) -> Review | None:
    with _conn() as con:
        row = con.execute("select * from reviews where id = ?", (review_id,)).fetchone()
        return _row_to_review(row) if row else None


def list_reviews(limit: int = 50) -> list[Review]:
    with _conn() as con:
        rows = con.execute(
            "select * from reviews order by created_at desc limit ?", (limit,)
        ).fetchall()
        return [_row_to_review(r) for r in rows]


def upsert_installation(inst_id: int, account: str, account_type: str,
                        repo_count: int, created_at: str) -> None:
    with _conn() as con:
        con.execute(
            """insert into installations (id, account, account_type, repo_count, created_at, suspended)
               values (?,?,?,?,?,0)
               on conflict(id) do update set
                 account=excluded.account, account_type=excluded.account_type,
                 repo_count=excluded.repo_count, suspended=0""",
            (inst_id, account, account_type, repo_count, created_at),
        )


def set_installation_suspended(inst_id: int, suspended: bool) -> None:
    with _conn() as con:
        con.execute("update installations set suspended=? where id=?",
                    (int(suspended), inst_id))


def delete_installation(inst_id: int) -> None:
    with _conn() as con:
        con.execute("delete from installations where id=?", (inst_id,))


def stats() -> dict:
    with _conn() as con:
        row = con.execute(
            """select
                 count(*) as total_reviews,
                 coalesce(sum(gated), 0) as gated_count,
                 coalesce(round(avg(risk_score), 2), 0) as avg_risk
               from reviews where status = 'completed'"""
        ).fetchone()
        findings_rows = con.execute(
            "select findings_json from reviews where status = 'completed'"
        ).fetchall()
    total_findings = sum(len(json.loads(r["findings_json"] or "[]")) for r in findings_rows)
    return {
        "total_reviews": row["total_reviews"],
        "gated_count": row["gated_count"],
        "avg_risk": row["avg_risk"],
        "total_findings": total_findings,
    }

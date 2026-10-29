"""SQLite connection and schema lifecycle helpers.

Only raw SQL is used in this project.  Connections are short-lived and created
per request so FastAPI's thread pool cannot accidentally share a connection.
"""

from __future__ import annotations

import os
import sqlite3
from contextlib import closing
from pathlib import Path
from typing import Iterator

from fastapi import HTTPException, Request

ROOT_DIR = Path(__file__).resolve().parent.parent
DEFAULT_DB_PATH = ROOT_DIR / "db" / "recruiterflow.db"
SCHEMA_PATH = ROOT_DIR / "db" / "schema.sql"

# Child tables first so the drops work even when PRAGMA foreign_keys is ON.
_DROP_SQL = """
DROP TABLE IF EXISTS culture_trait_affinities;
DROP TABLE IF EXISTS candidate_skills;
DROP TABLE IF EXISTS candidate_traits;
DROP TABLE IF EXISTS job_skills;
DROP TABLE IF EXISTS job_culture_keywords;
DROP TABLE IF EXISTS candidates;
DROP TABLE IF EXISTS jobs;
DROP TABLE IF EXISTS skills;
DROP TABLE IF EXISTS traits;
DROP TABLE IF EXISTS culture_keywords;
"""


def resolve_db_path(value: str | Path | None = None) -> Path:
    if value is not None:
        return Path(value).expanduser().resolve()
    env_value = os.environ.get("RECRUITERFLOW_DB")
    if env_value:
        return Path(env_value).expanduser().resolve()
    return DEFAULT_DB_PATH


def connect(db_path: str | Path) -> sqlite3.Connection:
    """Open a connection with row access by column name and FKs enforced."""
    path = Path(db_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(path, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def get_db(request: Request) -> Iterator[sqlite3.Connection]:
    """FastAPI dependency: one connection per request, always closed."""
    try:
        conn = connect(request.app.state.db_path)
    except sqlite3.Error as exc:  # e.g. an unreadable path
        raise HTTPException(status_code=503, detail="Database unavailable") from exc

    try:
        yield conn
    finally:
        conn.close()


def recreate_schema(db_path: str | Path) -> None:
    """Drop every Recruiter Bot table and recreate the schema.

    This is intentionally destructive: it is used by the seed script and by
    tests to guarantee a repeatable starting state.
    """
    path = Path(db_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    schema_sql = SCHEMA_PATH.read_text(encoding="utf-8")

    with closing(connect(path)) as conn:
        conn.executescript(_DROP_SQL)
        conn.executescript(schema_sql)
        conn.commit()


def schema_exists(db_path: str | Path) -> bool:
    path = Path(db_path)
    if not path.exists():
        return False
    with closing(connect(path)) as conn:
        row = conn.execute(
            "SELECT 1 FROM sqlite_master WHERE type = 'table' AND name = 'candidates'"
        ).fetchone()
    return row is not None

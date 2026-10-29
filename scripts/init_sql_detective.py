"""Create and load the separate SQL Detective dataset.

Usage:
    python -m scripts.init_sql_detective [--db db/sql_detective.db]

The schema and seed files are copied from the assignment and are never
regenerated from the Part 1 application model.
"""

from __future__ import annotations

import argparse
import sqlite3
from contextlib import closing
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SCHEMA = ROOT / "sql_detective" / "schema.sql"
SEED = ROOT / "sql_detective" / "seed.sql"
DEFAULT_DB = ROOT / "db" / "sql_detective.db"

DROP_SQL = """
DROP TABLE IF EXISTS interviews;
DROP TABLE IF EXISTS applicants;
DROP TABLE IF EXISTS job_postings;
DROP TABLE IF EXISTS recruiters;
"""


def init_sql_detective(db_path: str | Path = DEFAULT_DB) -> Path:
    path = Path(db_path).expanduser().resolve()
    path.parent.mkdir(parents=True, exist_ok=True)
    schema = SCHEMA.read_text(encoding="utf-8")
    seed = SEED.read_text(encoding="utf-8")

    with closing(sqlite3.connect(path)) as conn:
        conn.executescript(DROP_SQL)
        conn.executescript(schema)
        conn.executescript(seed)
        conn.commit()
    return path


def main() -> None:
    parser = argparse.ArgumentParser(description="Rebuild the SQL Detective database")
    parser.add_argument("--db", default=str(DEFAULT_DB))
    args = parser.parse_args()
    path = init_sql_detective(args.db)
    print(f"Initialised SQL Detective database at {path}")


if __name__ == "__main__":
    main()

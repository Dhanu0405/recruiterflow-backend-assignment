"""Execute every statement in sql_detective.sql and print the result sets.

Usage:
    python -m scripts.run_sql_detective [--db db/sql_detective.db]
"""

from __future__ import annotations

import argparse
import sqlite3
from contextlib import closing
from pathlib import Path

from scripts.init_sql_detective import DEFAULT_DB, init_sql_detective

ROOT = Path(__file__).resolve().parent.parent
QUERIES = ROOT / "sql_detective.sql"


def read_queries() -> list[str]:
    raw = QUERIES.read_text(encoding="utf-8")
    # This file intentionally contains no semicolons inside comments, so a
    # simple split is enough for local inspection.  Tests execute the same
    # statements through SQLite to verify the results.
    return [part.strip() for part in raw.split(";") if part.strip()]


def main() -> None:
    parser = argparse.ArgumentParser(description="Run the SQL Detective queries")
    parser.add_argument("--db", default=str(DEFAULT_DB))
    parser.add_argument(
        "--no-rebuild",
        action="store_true",
        help="Use an existing database instead of reloading schema and seed data",
    )
    args = parser.parse_args()

    path = Path(args.db).expanduser().resolve()
    if not args.no_rebuild or not path.exists():
        init_sql_detective(path)

    with closing(sqlite3.connect(path)) as conn:
        conn.row_factory = sqlite3.Row
        for index, statement in enumerate(read_queries(), start=1):
            rows = conn.execute(statement).fetchall()
            print(f"\n=== Query {index} ({len(rows)} rows) ===")
            if not rows:
                print("(empty)")
                continue
            print(" | ".join(rows[0].keys()))
            for row in rows:
                print(" | ".join("" if value is None else str(value) for value in row))


if __name__ == "__main__":
    main()

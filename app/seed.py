"""Repeatable database seeding.

Run with ``python -m app.seed`` (optionally ``--db path/to/file.db``).

The function first clears all content tables and then inserts the canonical
15 candidates and 6 jobs.  Running it twice can therefore never duplicate rows.
Schema recreation is handled separately by ``app.db.recreate_schema`` so the
seed function itself is also safe to call repeatedly against an existing schema.
"""

from __future__ import annotations

import argparse
import sqlite3
from contextlib import closing
from pathlib import Path

from app.db import connect, recreate_schema, resolve_db_path
from app.seed_data import CANDIDATES, CULTURE_TRAIT_AFFINITIES, JOBS

_CLEAR_SQL = """
DELETE FROM culture_trait_affinities;
DELETE FROM candidate_skills;
DELETE FROM candidate_traits;
DELETE FROM job_skills;
DELETE FROM job_culture_keywords;
DELETE FROM candidates;
DELETE FROM jobs;
DELETE FROM skills;
DELETE FROM traits;
DELETE FROM culture_keywords;
"""


def _all_skills() -> list[str]:
    values = {skill for candidate in CANDIDATES for skill in candidate["skills"]}
    values.update(skill for job in JOBS for skill in job["skills"])
    return sorted(values)


def _all_traits() -> list[str]:
    values = {trait for candidate in CANDIDATES for trait in candidate["traits"]}
    values.update(trait for traits in CULTURE_TRAIT_AFFINITIES.values() for trait in traits)
    return sorted(values)


def _all_culture_keywords() -> list[str]:
    values = {keyword for job in JOBS for keyword in job["culture_keywords"]}
    values.update(CULTURE_TRAIT_AFFINITIES)
    return sorted(values)


def seed_database(conn: sqlite3.Connection) -> dict[str, int]:
    """Insert the canonical dataset and return table counts.

    All SQL is static and every value is passed as a parameter.
    """
    skills = _all_skills()
    traits = _all_traits()
    keywords = _all_culture_keywords()

    missing_traits = {
        trait
        for mapped in CULTURE_TRAIT_AFFINITIES.values()
        for trait in mapped
        if trait not in traits
    }
    if missing_traits:  # defensive: catches typos in the affinity map
        raise ValueError(f"Unknown traits in culture map: {sorted(missing_traits)}")

    with conn:  # transaction
        conn.executescript(_CLEAR_SQL)

        for skill in skills:
            conn.execute("INSERT INTO skills (name) VALUES (?)", (skill,))
        for trait in traits:
            conn.execute("INSERT INTO traits (name) VALUES (?)", (trait,))
        for keyword in keywords:
            conn.execute(
                "INSERT INTO culture_keywords (name) VALUES (?)", (keyword,)
            )

        skill_ids = {
            row["name"]: row["id"]
            for row in conn.execute("SELECT id, name FROM skills").fetchall()
        }
        trait_ids = {
            row["name"]: row["id"]
            for row in conn.execute("SELECT id, name FROM traits").fetchall()
        }
        keyword_ids = {
            row["name"]: row["id"]
            for row in conn.execute("SELECT id, name FROM culture_keywords").fetchall()
        }

        for candidate in CANDIDATES:
            conn.execute(
                """
                INSERT INTO candidates
                    (id, name, experience_years, availability, quirk)
                VALUES (?, ?, ?, ?, ?)
                """,
                (
                    candidate["id"],
                    candidate["name"],
                    candidate["experience_years"],
                    candidate["availability"],
                    candidate["quirk"],
                ),
            )
            for skill in candidate["skills"]:
                conn.execute(
                    "INSERT INTO candidate_skills (candidate_id, skill_id) VALUES (?, ?)",
                    (candidate["id"], skill_ids[skill]),
                )
            for trait in candidate["traits"]:
                conn.execute(
                    "INSERT INTO candidate_traits (candidate_id, trait_id) VALUES (?, ?)",
                    (candidate["id"], trait_ids[trait]),
                )

        for job in JOBS:
            conn.execute(
                """
                INSERT INTO jobs (id, title, min_experience_years, tagline)
                VALUES (?, ?, ?, ?)
                """,
                (
                    job["id"],
                    job["title"],
                    job["min_experience_years"],
                    job["tagline"],
                ),
            )
            for skill in job["skills"]:
                conn.execute(
                    "INSERT INTO job_skills (job_id, skill_id) VALUES (?, ?)",
                    (job["id"], skill_ids[skill]),
                )
            for keyword in job["culture_keywords"]:
                conn.execute(
                    """
                    INSERT INTO job_culture_keywords (job_id, keyword_id)
                    VALUES (?, ?)
                    """,
                    (job["id"], keyword_ids[keyword]),
                )

        for keyword, mapped_traits in CULTURE_TRAIT_AFFINITIES.items():
            for trait in mapped_traits:
                conn.execute(
                    """
                    INSERT INTO culture_trait_affinities (keyword_id, trait_id)
                    VALUES (?, ?)
                    """,
                    (keyword_ids[keyword], trait_ids[trait]),
                )

    return table_counts(conn)


def table_counts(conn: sqlite3.Connection) -> dict[str, int]:
    return {
        "candidates": conn.execute("SELECT COUNT(*) FROM candidates").fetchone()[0],
        "jobs": conn.execute("SELECT COUNT(*) FROM jobs").fetchone()[0],
        "skills": conn.execute("SELECT COUNT(*) FROM skills").fetchone()[0],
        "traits": conn.execute("SELECT COUNT(*) FROM traits").fetchone()[0],
        "culture_keywords": conn.execute(
            "SELECT COUNT(*) FROM culture_keywords"
        ).fetchone()[0],
        "candidate_skills": conn.execute(
            "SELECT COUNT(*) FROM candidate_skills"
        ).fetchone()[0],
        "candidate_traits": conn.execute(
            "SELECT COUNT(*) FROM candidate_traits"
        ).fetchone()[0],
        "job_skills": conn.execute("SELECT COUNT(*) FROM job_skills").fetchone()[0],
        "job_culture_keywords": conn.execute(
            "SELECT COUNT(*) FROM job_culture_keywords"
        ).fetchone()[0],
        "culture_trait_affinities": conn.execute(
            "SELECT COUNT(*) FROM culture_trait_affinities"
        ).fetchone()[0],
    }


def build_database(db_path: str | Path) -> dict[str, int]:
    """Recreate the schema and seed it from scratch."""
    recreate_schema(db_path)
    with closing(connect(db_path)) as conn:
        return seed_database(conn)


def main() -> None:
    parser = argparse.ArgumentParser(description="Rebuild and seed the Recruiter Bot database")
    parser.add_argument(
        "--db",
        default=None,
        help="SQLite file path (defaults to db/recruiterflow.db or RECRUITERFLOW_DB)",
    )
    args = parser.parse_args()
    db_path = resolve_db_path(args.db)
    counts = build_database(db_path)
    print(f"Seeded {db_path}")
    for name, count in counts.items():
        print(f"  {name}: {count}")


if __name__ == "__main__":
    main()

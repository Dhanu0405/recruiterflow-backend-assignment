from __future__ import annotations

from app.seed import build_database, seed_database, table_counts
from app.seed_data import CANDIDATES, JOBS


def test_seed_contains_exactly_the_brief_dataset(db_conn):
    candidate_names = [
        row["name"]
        for row in db_conn.execute("SELECT name FROM candidates ORDER BY id").fetchall()
    ]
    job_titles = [
        row["title"]
        for row in db_conn.execute("SELECT title FROM jobs ORDER BY id").fetchall()
    ]

    assert candidate_names == [candidate["name"] for candidate in CANDIDATES]
    assert job_titles == [job["title"] for job in JOBS]
    assert len(candidate_names) == 15
    assert len(set(candidate_names)) == 15
    assert len(job_titles) == 6
    assert len(set(job_titles)) == 6

    counts = table_counts(db_conn)
    assert counts["candidates"] == 15
    assert counts["jobs"] == 6
    assert counts["candidate_skills"] == sum(
        len(candidate["skills"]) for candidate in CANDIDATES
    )
    assert counts["candidate_traits"] == sum(
        len(candidate["traits"]) for candidate in CANDIDATES
    )
    assert counts["job_skills"] == sum(len(job["skills"]) for job in JOBS)
    assert counts["job_culture_keywords"] == sum(
        len(job["culture_keywords"]) for job in JOBS
    )


def test_relationships_preserve_exact_skills_and_traits(db_conn):
    sherlock_skills = [
        row["name"]
        for row in db_conn.execute(
            """
            SELECT s.name
            FROM candidate_skills AS cs
            JOIN skills AS s ON s.id = cs.skill_id
            WHERE cs.candidate_id = 1
            ORDER BY s.name
            """
        ).fetchall()
    ]
    sherlock_traits = [
        row["name"]
        for row in db_conn.execute(
            """
            SELECT t.name
            FROM candidate_traits AS ct
            JOIN traits AS t ON t.id = ct.trait_id
            WHERE ct.candidate_id = 1
            ORDER BY t.name
            """
        ).fetchall()
    ]
    detective_skills = [
        row["name"]
        for row in db_conn.execute(
            """
            SELECT s.name
            FROM job_skills AS js
            JOIN skills AS s ON s.id = js.skill_id
            WHERE js.job_id = 1
            ORDER BY s.name
            """
        ).fetchall()
    ]

    assert sherlock_skills == ["deduction", "forensics", "pattern-recognition"]
    assert sherlock_traits == ["analytical", "blunt"]
    assert detective_skills == ["deduction", "forensics", "pattern-recognition"]


def test_every_seeded_field_matches_the_brief_source(db_conn):
    candidate_rows = {
        row["id"]: row
        for row in db_conn.execute(
            "SELECT id, name, experience_years, availability, quirk FROM candidates"
        ).fetchall()
    }
    for expected in CANDIDATES:
        row = candidate_rows[expected["id"]]
        assert row["name"] == expected["name"]
        assert row["experience_years"] == expected["experience_years"]
        assert row["availability"] == expected["availability"]
        assert row["quirk"] == expected["quirk"]

    job_rows = {
        row["id"]: row
        for row in db_conn.execute(
            "SELECT id, title, min_experience_years, tagline FROM jobs"
        ).fetchall()
    }
    for expected in JOBS:
        row = job_rows[expected["id"]]
        assert row["title"] == expected["title"]
        assert row["min_experience_years"] == expected["min_experience_years"]
        assert row["tagline"] == expected["tagline"]

    candidate_skills = {}
    for row in db_conn.execute(
        """
        SELECT cs.candidate_id, s.name
        FROM candidate_skills AS cs
        JOIN skills AS s ON s.id = cs.skill_id
        """
    ).fetchall():
        candidate_skills.setdefault(row["candidate_id"], []).append(row["name"])

    candidate_traits = {}
    for row in db_conn.execute(
        """
        SELECT ct.candidate_id, t.name
        FROM candidate_traits AS ct
        JOIN traits AS t ON t.id = ct.trait_id
        """
    ).fetchall():
        candidate_traits.setdefault(row["candidate_id"], []).append(row["name"])

    job_skills = {}
    for row in db_conn.execute(
        """
        SELECT js.job_id, s.name
        FROM job_skills AS js
        JOIN skills AS s ON s.id = js.skill_id
        """
    ).fetchall():
        job_skills.setdefault(row["job_id"], []).append(row["name"])

    job_culture = {}
    for row in db_conn.execute(
        """
        SELECT jck.job_id, ck.name
        FROM job_culture_keywords AS jck
        JOIN culture_keywords AS ck ON ck.id = jck.keyword_id
        """
    ).fetchall():
        job_culture.setdefault(row["job_id"], []).append(row["name"])

    for expected in CANDIDATES:
        assert sorted(candidate_skills[expected["id"]]) == sorted(expected["skills"])
        assert sorted(candidate_traits[expected["id"]]) == sorted(expected["traits"])

    for expected in JOBS:
        assert sorted(job_skills[expected["id"]]) == sorted(expected["skills"])
        assert sorted(job_culture[expected["id"]]) == sorted(
            expected["culture_keywords"]
        )


def test_no_duplicate_identity_rows(db_conn):
    duplicate_checks = (
        "SELECT name, COUNT(*) AS n FROM candidates GROUP BY name HAVING COUNT(*) > 1",
        "SELECT title, COUNT(*) AS n FROM jobs GROUP BY title HAVING COUNT(*) > 1",
        "SELECT name, COUNT(*) AS n FROM skills GROUP BY name HAVING COUNT(*) > 1",
        "SELECT name, COUNT(*) AS n FROM traits GROUP BY name HAVING COUNT(*) > 1",
        "SELECT name, COUNT(*) AS n FROM culture_keywords GROUP BY name HAVING COUNT(*) > 1",
    )
    for statement in duplicate_checks:
        assert db_conn.execute(statement).fetchall() == []


def test_reseeding_is_idempotent(tmp_path):
    path = tmp_path / "idempotent.db"

    first = build_database(path)
    second = build_database(path)
    assert first == second
    assert second["candidates"] == 15
    assert second["jobs"] == 6

    # Calling the seed function repeatedly on an existing schema must also
    # leave exactly one copy of every record.
    from contextlib import closing

    from app.db import connect

    with closing(connect(path)) as conn:
        third = seed_database(conn)
        fourth = seed_database(conn)
    assert third == fourth
    assert fourth["candidates"] == 15
    assert fourth["jobs"] == 6

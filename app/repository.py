"""Data access layer: hand-written SQL only.

Every query is a static string and every value that comes from outside is
passed as a bound parameter.  There is no ORM, no query builder, no dynamic
SQL construction and no string interpolation of user input anywhere.
"""

from __future__ import annotations

import sqlite3
from collections import defaultdict

from app.domain import Candidate, Job


def _load_candidate_skills(conn: sqlite3.Connection) -> dict[int, list[str]]:
    rows = conn.execute(
        """
        SELECT cs.candidate_id, s.name
        FROM candidate_skills AS cs
        JOIN skills AS s ON s.id = cs.skill_id
        ORDER BY cs.candidate_id, s.name
        """
    ).fetchall()
    result: dict[int, list[str]] = defaultdict(list)
    for row in rows:
        result[row["candidate_id"]].append(row["name"])
    return result


def _load_candidate_traits(conn: sqlite3.Connection) -> dict[int, list[str]]:
    rows = conn.execute(
        """
        SELECT ct.candidate_id, t.name
        FROM candidate_traits AS ct
        JOIN traits AS t ON t.id = ct.trait_id
        ORDER BY ct.candidate_id, t.name
        """
    ).fetchall()
    result: dict[int, list[str]] = defaultdict(list)
    for row in rows:
        result[row["candidate_id"]].append(row["name"])
    return result


def fetch_all_candidates(conn: sqlite3.Connection) -> list[Candidate]:
    rows = conn.execute(
        """
        SELECT id, name, experience_years, availability, quirk
        FROM candidates
        ORDER BY id
        """
    ).fetchall()
    skills = _load_candidate_skills(conn)
    traits = _load_candidate_traits(conn)
    return [
        Candidate(
            id=row["id"],
            name=row["name"],
            experience_years=row["experience_years"],
            availability=row["availability"],
            quirk=row["quirk"],
            skills=tuple(skills.get(row["id"], [])),
            traits=tuple(traits.get(row["id"], [])),
        )
        for row in rows
    ]


def fetch_candidate(conn: sqlite3.Connection, candidate_id: int) -> Candidate | None:
    row = conn.execute(
        """
        SELECT id, name, experience_years, availability, quirk
        FROM candidates
        WHERE id = ?
        """,
        (candidate_id,),
    ).fetchone()
    if row is None:
        return None

    skill_rows = conn.execute(
        """
        SELECT s.name
        FROM candidate_skills AS cs
        JOIN skills AS s ON s.id = cs.skill_id
        WHERE cs.candidate_id = ?
        ORDER BY s.name
        """,
        (candidate_id,),
    ).fetchall()
    trait_rows = conn.execute(
        """
        SELECT t.name
        FROM candidate_traits AS ct
        JOIN traits AS t ON t.id = ct.trait_id
        WHERE ct.candidate_id = ?
        ORDER BY t.name
        """,
        (candidate_id,),
    ).fetchall()

    return Candidate(
        id=row["id"],
        name=row["name"],
        experience_years=row["experience_years"],
        availability=row["availability"],
        quirk=row["quirk"],
        skills=tuple(skill_row["name"] for skill_row in skill_rows),
        traits=tuple(trait_row["name"] for trait_row in trait_rows),
    )


def _load_job_skills(conn: sqlite3.Connection) -> dict[int, list[str]]:
    rows = conn.execute(
        """
        SELECT js.job_id, s.name
        FROM job_skills AS js
        JOIN skills AS s ON s.id = js.skill_id
        ORDER BY js.job_id, s.name
        """
    ).fetchall()
    result: dict[int, list[str]] = defaultdict(list)
    for row in rows:
        result[row["job_id"]].append(row["name"])
    return result


def _load_job_culture(conn: sqlite3.Connection) -> dict[int, list[str]]:
    rows = conn.execute(
        """
        SELECT jck.job_id, ck.name
        FROM job_culture_keywords AS jck
        JOIN culture_keywords AS ck ON ck.id = jck.keyword_id
        ORDER BY jck.job_id, ck.name
        """
    ).fetchall()
    result: dict[int, list[str]] = defaultdict(list)
    for row in rows:
        result[row["job_id"]].append(row["name"])
    return result


def fetch_all_jobs(conn: sqlite3.Connection) -> list[Job]:
    rows = conn.execute(
        """
        SELECT id, title, min_experience_years, tagline
        FROM jobs
        ORDER BY id
        """
    ).fetchall()
    skills = _load_job_skills(conn)
    culture = _load_job_culture(conn)
    return [
        Job(
            id=row["id"],
            title=row["title"],
            min_experience_years=row["min_experience_years"],
            tagline=row["tagline"],
            skills=tuple(skills.get(row["id"], [])),
            culture_keywords=tuple(culture.get(row["id"], [])),
        )
        for row in rows
    ]


def fetch_job(conn: sqlite3.Connection, job_id: int) -> Job | None:
    row = conn.execute(
        """
        SELECT id, title, min_experience_years, tagline
        FROM jobs
        WHERE id = ?
        """,
        (job_id,),
    ).fetchone()
    if row is None:
        return None

    skill_rows = conn.execute(
        """
        SELECT s.name
        FROM job_skills AS js
        JOIN skills AS s ON s.id = js.skill_id
        WHERE js.job_id = ?
        ORDER BY s.name
        """,
        (job_id,),
    ).fetchall()
    culture_rows = conn.execute(
        """
        SELECT ck.name
        FROM job_culture_keywords AS jck
        JOIN culture_keywords AS ck ON ck.id = jck.keyword_id
        WHERE jck.job_id = ?
        ORDER BY ck.name
        """,
        (job_id,),
    ).fetchall()

    return Job(
        id=row["id"],
        title=row["title"],
        min_experience_years=row["min_experience_years"],
        tagline=row["tagline"],
        skills=tuple(skill_row["name"] for skill_row in skill_rows),
        culture_keywords=tuple(
            culture_row["name"] for culture_row in culture_rows
        ),
    )


def fetch_culture_affinities(conn: sqlite3.Connection) -> dict[str, frozenset[str]]:
    rows = conn.execute(
        """
        SELECT ck.name AS keyword, t.name AS trait
        FROM culture_trait_affinities AS cta
        JOIN culture_keywords AS ck ON ck.id = cta.keyword_id
        JOIN traits AS t ON t.id = cta.trait_id
        ORDER BY ck.name, t.name
        """
    ).fetchall()
    grouped: dict[str, set[str]] = defaultdict(set)
    for row in rows:
        grouped[row["keyword"]].add(row["trait"])
    return {keyword: frozenset(traits) for keyword, traits in grouped.items()}

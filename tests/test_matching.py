from __future__ import annotations

import pytest

from app.domain import Candidate, Job
from app.matching import (
    AVAILABILITY_WEIGHT,
    CULTURE_WEIGHT,
    EXPERIENCE_WEIGHT,
    SKILL_WEIGHT,
    rank_candidates,
    rank_jobs,
    score_fit,
)
from app.repository import (
    fetch_all_candidates,
    fetch_all_jobs,
    fetch_candidate,
    fetch_culture_affinities,
    fetch_job,
)


def _candidate(**overrides) -> Candidate:
    values = {
        "id": 100,
        "name": "Test Candidate",
        "experience_years": 5,
        "availability": "Immediate",
        "quirk": "test",
        "skills": ("alpha", "beta"),
        "traits": (),
    }
    values.update(overrides)
    return Candidate(**values)


def _job(**overrides) -> Job:
    values = {
        "id": 200,
        "title": "Test Job",
        "min_experience_years": 5,
        "tagline": "test",
        "skills": ("alpha", "beta"),
        "culture_keywords": (),
    }
    values.update(overrides)
    return Job(**values)


def test_known_pair_scores_95_with_correct_breakdown(db_conn):
    candidate = fetch_candidate(db_conn, 1)
    job = fetch_job(db_conn, 1)
    affinities = fetch_culture_affinities(db_conn)

    score = score_fit(candidate, job, affinities)

    assert score.total == 95.0
    assert score.skill_points == 55.0
    assert score.experience_points == 25.0
    assert score.availability_points == 10.0
    assert score.culture_points == 5.0
    assert score.matched_skills == (
        "deduction",
        "forensics",
        "pattern-recognition",
    )
    assert score.missing_skills == ()
    assert score.matched_culture_keywords == ("analytical",)
    assert "matches 3/3 required skills" in score.explanation
    assert "available immediately" in score.explanation


def test_skill_overlap_directly_changes_score():
    job = _job(skills=("alpha", "beta", "gamma"), min_experience_years=1)
    full = _candidate(skills=("alpha", "beta", "gamma"))
    partial = _candidate(skills=("alpha",))
    none = _candidate(skills=("unrelated",))

    full_score = score_fit(full, job, {})
    partial_score = score_fit(partial, job, {})
    none_score = score_fit(none, job, {})

    assert full_score.skill_points == SKILL_WEIGHT
    assert partial_score.skill_points == pytest.approx(SKILL_WEIGHT / 3, abs=0.01)
    assert none_score.skill_points == 0.0
    assert full_score.total > partial_score.total > none_score.total
    assert full_score.total - none_score.total == pytest.approx(55.0)


def test_experience_shortfall_reduces_score_and_is_explained():
    job = _job(min_experience_years=10)
    meets = _candidate(experience_years=10)
    short = _candidate(experience_years=5)

    meets_score = score_fit(meets, job, {})
    short_score = score_fit(short, job, {})

    assert meets_score.experience_points == EXPERIENCE_WEIGHT
    assert short_score.experience_points == pytest.approx(12.5)
    assert meets_score.total > short_score.total
    assert "short by 5" in short_score.explanation


def test_availability_and_culture_are_capped_soft_signals(db_conn):
    candidate = fetch_candidate(db_conn, 3)  # Tony: Not looking
    job = fetch_job(db_conn, 2)  # Rapid Prototyping Engineer
    affinities = fetch_culture_affinities(db_conn)

    score = score_fit(candidate, job, affinities)

    assert score.skill_points == SKILL_WEIGHT
    assert score.experience_points == EXPERIENCE_WEIGHT
    assert score.availability_points == 2.0  # 10 * 0.2
    assert score.culture_points == CULTURE_WEIGHT
    assert score.availability_points <= AVAILABILITY_WEIGHT
    assert score.culture_points <= CULTURE_WEIGHT


def test_every_seeded_pair_is_bounded_and_consistent(db_conn):
    candidates = fetch_all_candidates(db_conn)
    jobs = fetch_all_jobs(db_conn)
    affinities = fetch_culture_affinities(db_conn)

    for candidate in candidates:
        for job in jobs:
            score = score_fit(candidate, job, affinities)
            assert 0.0 <= score.total <= 100.0
            component_sum = (
                score.skill_points
                + score.experience_points
                + score.availability_points
                + score.culture_points
            )
            assert score.total == pytest.approx(component_sum, abs=0.05)
            assert score.explanation.endswith(".")
            assert len(score.explanation) > 40

    # Forward and reverse endpoints must produce the same score for a pair.
    forward = score_fit(candidates[0], jobs[0], affinities)
    reverse = {
        job.id: score
        for job, score in rank_jobs(candidates[0], jobs, affinities)
    }[jobs[0].id]
    assert forward == reverse


def test_ranking_is_deterministic_and_ties_break_by_name(db_conn):
    job = fetch_job(db_conn, 1)
    candidates = fetch_all_candidates(db_conn)
    affinities = fetch_culture_affinities(db_conn)

    first = rank_candidates(job, candidates, affinities)
    second = rank_candidates(job, candidates, affinities)
    assert [candidate.id for candidate, _ in first] == [
        candidate.id for candidate, _ in second
    ]
    assert first[0][0].name == "Sherlock H."

    tied_job = _job(skills=(), min_experience_years=0, culture_keywords=())
    bob = _candidate(id=2, name="Bob", skills=())
    ada = _candidate(id=1, name="Ada", skills=())
    ranked = rank_candidates(tied_job, [bob, ada], {})
    assert [candidate.name for candidate, _ in ranked] == ["Ada", "Bob"]


def test_reverse_ranking_is_sorted_and_backend_detective_wins_for_sherlock(db_conn):
    candidate = fetch_candidate(db_conn, 1)
    jobs = fetch_all_jobs(db_conn)
    affinities = fetch_culture_affinities(db_conn)

    ranked = rank_jobs(candidate, jobs, affinities)

    scores = [score.total for _, score in ranked]
    assert scores == sorted(scores, reverse=True)
    assert ranked[0][0].id == 1
    assert ranked[0][0].title == "Backend Detective"
    assert ranked[0][1].total == 95.0

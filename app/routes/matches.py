"""Health and match endpoints."""

from __future__ import annotations

import sqlite3
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Path

from app.db import get_db
from app.matching import (
    AVAILABILITY_WEIGHT,
    CULTURE_WEIGHT,
    EXPERIENCE_WEIGHT,
    SKILL_WEIGHT,
    MatchScore,
    rank_candidates,
    rank_jobs,
)
from app.repository import (
    fetch_all_candidates,
    fetch_all_jobs,
    fetch_candidate,
    fetch_culture_affinities,
    fetch_job,
)
from app.schemas import (
    CandidateMatchItem,
    CandidateMatchesResponse,
    CandidateSummary,
    JobMatchItem,
    JobMatchesResponse,
    JobSummary,
    ScoreBreakdown,
    ScoringInfo,
    ScoringWeights,
)

router = APIRouter()

SCORING_INFO = ScoringInfo(
    weights=ScoringWeights(
        skills=SKILL_WEIGHT,
        experience=EXPERIENCE_WEIGHT,
        availability=AVAILABILITY_WEIGHT,
        culture=CULTURE_WEIGHT,
    )
)


def _breakdown(score: MatchScore) -> ScoreBreakdown:
    return ScoreBreakdown(
        skills=score.skill_points,
        experience=score.experience_points,
        availability=score.availability_points,
        culture=score.culture_points,
    )


@router.get("/health", tags=["health"])
def health(conn: sqlite3.Connection = Depends(get_db)) -> dict[str, object]:
    try:
        conn.execute("SELECT 1").fetchone()
        candidates = conn.execute("SELECT COUNT(*) FROM candidates").fetchone()[0]
        jobs = conn.execute("SELECT COUNT(*) FROM jobs").fetchone()[0]
    except sqlite3.Error as exc:
        raise HTTPException(status_code=503, detail="Database unavailable") from exc
    return {
        "status": "ok",
        "database": "ok",
        "candidates": candidates,
        "jobs": jobs,
    }


@router.get(
    "/jobs/{job_id}/matches",
    response_model=JobMatchesResponse,
    tags=["matches"],
)
def job_matches(
    job_id: Annotated[int, Path(ge=1)],
    conn: sqlite3.Connection = Depends(get_db),
) -> JobMatchesResponse:
    try:
        job = fetch_job(conn, job_id)
        if job is None:
            raise HTTPException(status_code=404, detail=f"Job {job_id} was not found")
        candidates = fetch_all_candidates(conn)
        affinities = fetch_culture_affinities(conn)
    except sqlite3.Error as exc:
        raise HTTPException(
            status_code=503, detail="Database error while matching candidates"
        ) from exc

    ranked = rank_candidates(job, candidates, affinities)
    results = [
        CandidateMatchItem(
            rank=rank,
            candidate_id=candidate.id,
            candidate_name=candidate.name,
            score=score.total,
            breakdown=_breakdown(score),
            matched_skills=list(score.matched_skills),
            missing_skills=list(score.missing_skills),
            matched_culture_keywords=list(score.matched_culture_keywords),
            explanation=score.explanation,
        )
        for rank, (candidate, score) in enumerate(ranked, start=1)
    ]

    return JobMatchesResponse(
        job=JobSummary(id=job.id, title=job.title),
        count=len(results),
        scoring=SCORING_INFO,
        results=results,
    )


@router.get(
    "/candidates/{candidate_id}/matches",
    response_model=CandidateMatchesResponse,
    tags=["matches"],
)
def candidate_matches(
    candidate_id: Annotated[int, Path(ge=1)],
    conn: sqlite3.Connection = Depends(get_db),
) -> CandidateMatchesResponse:
    try:
        candidate = fetch_candidate(conn, candidate_id)
        if candidate is None:
            raise HTTPException(
                status_code=404, detail=f"Candidate {candidate_id} was not found"
            )
        jobs = fetch_all_jobs(conn)
        affinities = fetch_culture_affinities(conn)
    except sqlite3.Error as exc:
        raise HTTPException(
            status_code=503, detail="Database error while matching jobs"
        ) from exc

    ranked = rank_jobs(candidate, jobs, affinities)
    results = [
        JobMatchItem(
            rank=rank,
            job_id=job.id,
            job_title=job.title,
            score=score.total,
            breakdown=_breakdown(score),
            matched_skills=list(score.matched_skills),
            missing_skills=list(score.missing_skills),
            matched_culture_keywords=list(score.matched_culture_keywords),
            explanation=score.explanation,
        )
        for rank, (job, score) in enumerate(ranked, start=1)
    ]

    return CandidateMatchesResponse(
        candidate=CandidateSummary(id=candidate.id, name=candidate.name),
        count=len(results),
        scoring=SCORING_INFO,
        results=results,
    )

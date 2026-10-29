"""Pydantic response models for the public API."""

from __future__ import annotations

from pydantic import BaseModel


class JobSummary(BaseModel):
    id: int
    title: str


class CandidateSummary(BaseModel):
    id: int
    name: str


class ScoringWeights(BaseModel):
    skills: float
    experience: float
    availability: float
    culture: float


class ScoringInfo(BaseModel):
    scale: str = "0-100"
    weights: ScoringWeights


class ScoreBreakdown(BaseModel):
    skills: float
    experience: float
    availability: float
    culture: float


class CandidateMatchItem(BaseModel):
    rank: int
    candidate_id: int
    candidate_name: str
    score: float
    breakdown: ScoreBreakdown
    matched_skills: list[str]
    missing_skills: list[str]
    matched_culture_keywords: list[str]
    explanation: str


class JobMatchesResponse(BaseModel):
    job: JobSummary
    count: int
    scoring: ScoringInfo
    results: list[CandidateMatchItem]


class JobMatchItem(BaseModel):
    rank: int
    job_id: int
    job_title: str
    score: float
    breakdown: ScoreBreakdown
    matched_skills: list[str]
    missing_skills: list[str]
    matched_culture_keywords: list[str]
    explanation: str


class CandidateMatchesResponse(BaseModel):
    candidate: CandidateSummary
    count: int
    scoring: ScoringInfo
    results: list[JobMatchItem]

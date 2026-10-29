"""Deterministic candidate/job matching.

Scoring formula (total is always on a 0-100 scale):

    score = 55 * skill_coverage
          + 25 * experience_fit
          + 10 * availability_fit
          + 10 * culture_fit

* skill_coverage   = matched required skills / required skills. Extra
                     candidate skills earn no bonus; requirements are treated
                     as must-haves.
* experience_fit   = 1.0 when candidate years >= job minimum, otherwise
                     candidate years / minimum years. Surplus experience is
                     not penalised because minimums are thresholds, not caps.
* availability_fit = Immediate 1.0, 2 weeks 0.6, Not looking 0.2. "Not looking"
                     is a soft penalty rather than a hard exclusion.
* culture_fit      = matched culture keywords / job culture keywords, using the
                     explicit culture_trait_affinities bridge table. A keyword
                     counts as matched when at least one related trait is on
                     the candidate. This is a small soft signal (10%).

Every component is rounded to two decimals for display. Ranking uses the
score descending, then skill coverage, experience fit, a case-insensitive name
tie-break and finally the numeric id. That makes results fully reproducible.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable, Mapping

from app.domain import Candidate, Job

SKILL_WEIGHT = 55.0
EXPERIENCE_WEIGHT = 25.0
AVAILABILITY_WEIGHT = 10.0
CULTURE_WEIGHT = 10.0

AVAILABILITY_FIT = {
    "Immediate": 1.0,
    "2 weeks": 0.6,
    "Not looking": 0.2,
}

AVAILABILITY_PHRASES = {
    "Immediate": "available immediately",
    "2 weeks": "available in 2 weeks",
    "Not looking": "not currently looking",
}


@dataclass(frozen=True)
class MatchScore:
    total: float
    skill_points: float
    experience_points: float
    availability_points: float
    culture_points: float
    skill_coverage: float
    experience_fit: float
    availability_fit: float
    culture_fit: float
    matched_skills: tuple[str, ...]
    missing_skills: tuple[str, ...]
    matched_culture_keywords: tuple[str, ...]
    explanation: str


def _normalise(value: str) -> str:
    return " ".join(value.strip().lower().split())


def _round(value: float) -> float:
    return round(value, 2)


def score_fit(
    candidate: Candidate,
    job: Job,
    affinities: Mapping[str, frozenset[str]],
) -> MatchScore:
    """Score one candidate against one job. Pure and deterministic."""
    candidate_skill_set = {_normalise(skill) for skill in candidate.skills}
    required_skills = sorted(job.skills)

    if required_skills:
        matched = tuple(
            skill
            for skill in required_skills
            if _normalise(skill) in candidate_skill_set
        )
        missing = tuple(
            skill
            for skill in required_skills
            if _normalise(skill) not in candidate_skill_set
        )
        skill_coverage = len(matched) / len(required_skills)
    else:
        matched = ()
        missing = ()
        skill_coverage = 1.0

    minimum = max(job.min_experience_years, 0)
    if minimum == 0 or candidate.experience_years >= minimum:
        experience_fit = 1.0
    else:
        experience_fit = max(0.0, candidate.experience_years / minimum)

    availability_fit = AVAILABILITY_FIT.get(candidate.availability, 0.0)

    candidate_traits = {_normalise(trait) for trait in candidate.traits}
    culture_keywords = sorted(job.culture_keywords)
    if culture_keywords:
        matched_culture = tuple(
            keyword
            for keyword in culture_keywords
            if candidate_traits
            & {_normalise(trait) for trait in affinities.get(_normalise(keyword), ())}
        )
        culture_fit = len(matched_culture) / len(culture_keywords)
    else:
        matched_culture = ()
        culture_fit = 1.0

    skill_points = SKILL_WEIGHT * skill_coverage
    experience_points = EXPERIENCE_WEIGHT * experience_fit
    availability_points = AVAILABILITY_WEIGHT * availability_fit
    culture_points = CULTURE_WEIGHT * culture_fit
    total = (
        skill_points
        + experience_points
        + availability_points
        + culture_points
    )
    total = min(100.0, max(0.0, total))

    explanation = _build_explanation(
        candidate=candidate,
        job=job,
        matched=matched,
        missing=missing,
        required_count=len(required_skills),
        matched_culture=matched_culture,
        culture_count=len(culture_keywords),
    )

    return MatchScore(
        total=_round(total),
        skill_points=_round(skill_points),
        experience_points=_round(experience_points),
        availability_points=_round(availability_points),
        culture_points=_round(culture_points),
        skill_coverage=_round(skill_coverage),
        experience_fit=_round(experience_fit),
        availability_fit=_round(availability_fit),
        culture_fit=_round(culture_fit),
        matched_skills=matched,
        missing_skills=missing,
        matched_culture_keywords=matched_culture,
        explanation=explanation,
    )


def _build_explanation(
    *,
    candidate: Candidate,
    job: Job,
    matched: tuple[str, ...],
    missing: tuple[str, ...],
    required_count: int,
    matched_culture: tuple[str, ...],
    culture_count: int,
) -> str:
    if required_count:
        skill_text = f"matches {len(matched)}/{required_count} required skills"
        if matched:
            skill_text += f" ({', '.join(matched)})"
        if missing:
            skill_text += f"; missing {', '.join(missing)}"
    else:
        skill_text = "no required skills were specified"

    minimum = job.min_experience_years
    if candidate.experience_years >= minimum:
        experience_text = (
            f"meets the {minimum}-year minimum with "
            f"{candidate.experience_years} years"
            if minimum
            else f"no minimum experience required; has {candidate.experience_years} years"
        )
    else:
        shortfall = minimum - candidate.experience_years
        experience_text = (
            f"has {candidate.experience_years} years against a {minimum}-year "
            f"minimum (short by {shortfall})"
        )

    availability_text = AVAILABILITY_PHRASES.get(
        candidate.availability, f"availability is {candidate.availability.lower()}"
    )

    if culture_count:
        if matched_culture:
            culture_text = (
                f"culture fit on {len(matched_culture)}/{culture_count} keywords "
                f"({', '.join(matched_culture)})"
            )
        else:
            culture_text = (
                f"no culture-keyword overlap ({', '.join(sorted(job.culture_keywords))})"
            )
    else:
        culture_text = "no culture keywords to assess"

    return (
        f"Candidate {skill_text}; {experience_text}; {availability_text}; "
        f"{culture_text}."
    )


def rank_candidates(
    job: Job,
    candidates: Iterable[Candidate],
    affinities: Mapping[str, frozenset[str]],
) -> list[tuple[Candidate, MatchScore]]:
    scored = [(candidate, score_fit(candidate, job, affinities)) for candidate in candidates]
    scored.sort(
        key=lambda pair: (
            -pair[1].total,
            -pair[1].skill_coverage,
            -pair[1].experience_fit,
            pair[0].name.casefold(),
            pair[0].id,
        )
    )
    return scored


def rank_jobs(
    candidate: Candidate,
    jobs: Iterable[Job],
    affinities: Mapping[str, frozenset[str]],
) -> list[tuple[Job, MatchScore]]:
    scored = [(job, score_fit(candidate, job, affinities)) for job in jobs]
    scored.sort(
        key=lambda pair: (
            -pair[1].total,
            -pair[1].skill_coverage,
            -pair[1].experience_fit,
            pair[0].title.casefold(),
            pair[0].id,
        )
    )
    return scored

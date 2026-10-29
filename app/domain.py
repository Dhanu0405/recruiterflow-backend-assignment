"""Plain domain objects.

These are simple dataclasses, not ORM entities.  They exist only to keep the
matching code readable after rows have been loaded with hand-written SQL.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class Candidate:
    id: int
    name: str
    experience_years: int
    availability: str
    quirk: str
    skills: tuple[str, ...]
    traits: tuple[str, ...]


@dataclass(frozen=True)
class Job:
    id: int
    title: str
    min_experience_years: int
    tagline: str
    skills: tuple[str, ...]
    culture_keywords: tuple[str, ...]

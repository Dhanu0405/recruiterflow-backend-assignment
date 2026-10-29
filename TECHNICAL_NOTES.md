# Recruiter Bot — Technical Notes

This file records the implementation and scoring decisions for Section B. It is
deliberately not a submission README; installation/run notes will be written
later.

## Stack and structure

- Python 3.14, FastAPI, SQLite, `sqlite3` from the standard library.
- No ORM, query builder, or SQL-generating library. All application SQL is
  static, hand-written text with bound parameters.
- `app/main.py` creates the app; `app/routes/matches.py` exposes the endpoints;
  `app/repository.py` contains SQL access; `app/matching.py` contains the pure
  scoring and ranking logic.
- `app/seed_data.py` holds the assignment data and `app/seed.py` is the
  repeatable seed script. `db/schema.sql` contains the Part 1 DDL.
- Part 2 is separate: `sql_detective/schema.sql`, `sql_detective/seed.sql`, and
  `sql_detective.sql`. It is intentionally not tied to the Part 1 schema.

## Part 1 schema

Candidates, jobs, skills, traits, and culture keywords are stored as separate
entities. Junction tables (`candidate_skills`, `candidate_traits`, `job_skills`,
`job_culture_keywords`) preserve the many-to-many relationships and primary-key
constraints prevent duplicate links. `culture_trait_affinities` is an explicit,
reviewable bridge from a job culture keyword to a candidate trait; it avoids
fuzzy string matching at request time.

Seeding clears the content tables and inserts the canonical 15 candidates and 6
jobs. The operation is repeatable: running it again cannot duplicate records.
`python -m app.seed` also rebuilds the schema first for a clean local reset.

## Matching formula

Each candidate/job pair receives a score out of 100:

```
score = 55 * skill_coverage
      + 25 * experience_fit
      + 10 * availability_fit
      + 10 * culture_fit
```

### Skill coverage (55 points)

`matched required skills / total required skills`. Requirements are treated as
must-haves; having extra skills does not earn a bonus. If a job had no required
skills, full skill credit is given (not present in the supplied data).

### Experience fit (25 points)

- Candidate years >= job minimum: `1.0`.
- Candidate years < job minimum: `candidate years / minimum years` (clamped to
  the 0–1 range).
- A zero-year minimum gives full credit.

Surplus experience is not penalised: a minimum is a threshold, not a ceiling.
This keeps senior candidates such as Ron and Miranda eligible for junior roles
without inventing an overqualification penalty that the brief did not ask for.

### Availability (10 points)

| Availability | Fit |
|---|---:|
| Immediate | 1.0 |
| 2 weeks | 0.6 |
| Not looking | 0.2 |

This is a soft signal, not a hard filter. "Not looking" still receives a small
amount of credit so a strong skill/experience match remains visible.

### Culture/trait compatibility (10 points)

`matched culture keywords / job culture keywords`. A keyword matches when the
candidate has at least one trait listed for it in
`culture_trait_affinities`. The map is deliberately small and explicit, e.g.
`analytical` maps to analytical/sharp/brilliant/genius, and `calm-under-pressure`
maps to calm/resilient/decisive. It is a 10% tie-breaker-style signal rather
than a personality test. The mapping is subjective; keeping it in a table makes
it easy to audit and change without touching scoring code.

## Ranking and determinism

Scores are rounded to two decimals for display. Results are sorted by:

1. score descending,
2. skill coverage descending,
3. experience fit descending,
4. case-insensitive candidate name (job direction) or job title (candidate
   direction) ascending,
5. numeric id ascending.

That makes ties deterministic. Both directions call the same pure
`score_fit()` function, so a candidate/job pair has the same score in either
endpoint.

Each result includes the component breakdown and a short explanation generated
from the same values used for scoring, so the reason cannot drift from the
number.

## API behaviour

- `GET /health` checks the database and reports the seeded counts.
- `GET /jobs/{id}/matches` returns all candidates ranked for that job.
- `GET /candidates/{id}/matches` returns all jobs ranked for that candidate.
- Missing IDs return 404. Non-positive or non-integer IDs return 422.
- A valid request against an empty candidate table returns 200 with an empty
  result list.
- Database query errors return 503 rather than leaking SQLite details.

## SQL Detective decisions

- Q1 joins open postings to their recruiter and orders by opening date.
- Q2 counts distinct applicants at the Final stage per posting and uses a LEFT
  JOIN so postings with no Final interviews still appear with zero.
- Q3 treats identity as `LOWER(TRIM(email))`; NULL/blank emails fall back to the
  applicant id so unrelated NULLs are never merged. It counts distinct job
  postings, not interview rows. This collapses the two differently capitalised
  Ananya Rao records. The supplied schema has no separate application-to-job
  table, so "applied to a posting" is inferred from having at least one
  interview row for that posting.
- Q4 counts every Final-stage interview in the denominator, including pending
  outcomes, and applies the `HAVING COUNT(*) >= 3` volume filter.
- Q5 uses `ROW_NUMBER()` partitioned by department. Ties are resolved by
  recruiter name and then id. Departments with no successful Final placement
  are not represented because the query starts from passed Final interviews. If
  co-winners should be returned, `RANK()` is the documented alternative.

## Known limitations / next steps

- Matching loads the small candidate/job dataset into Python and scores it in
  memory. That is appropriate for 15 candidates and 6 jobs, but a larger dataset
  would need pagination, pre-filtering, or SQL-side candidate reduction.
- The culture-affinity map is a judgement call; another reviewer could choose
  different synonyms. It is intentionally only 10% of the total.
- Availability and experience are modelled as continuous signals. A real
  recruiting system might add hard knockout rules or recruiter overrides.
- The API has no authentication, rate limiting, or write endpoints. The brief
  asks for ranking endpoints, not a full ATS.

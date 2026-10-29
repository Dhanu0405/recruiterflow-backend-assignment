# Recruiter Bot

A small, deterministic candidate-to-job matching backend built with **Python, FastAPI, and SQLite**. It ingests the fictional candidate/job dataset from the RecruiterFlow backend assignment, ranks matches in both directions, and explains every score with a component breakdown and a short reason.

This repository covers **Section B of the assignment only**: the Recruiter Bot backend (Part 1) and the SQL Detective challenge (Part 2).

## Features

- Ranked candidates for a job: `GET /jobs/{id}/matches`
- Ranked jobs for a candidate: `GET /candidates/{id}/matches`
- Explainable 0–100 scores with skill, experience, availability, and culture components
- Deterministic ranking with explicit tie-breakers
- Normalised SQLite schema with raw, parameterised SQL — no ORM or query builder
- Repeatable seed script with 15 candidates and 6 jobs
- Health check with database counts
- Five SQL Detective queries, including the bonus window-function query
- Automated tests for scoring, API behaviour, seeding, and SQL results

## Tech Stack

| Layer | Choice |
|---|---|
| Language | Python 3.14 (verified with 3.14.3) |
| API | FastAPI 0.162.0 |
| Server | Uvicorn 0.54.0 |
| Database | SQLite via Python's `sqlite3` standard library |
| Tests | pytest 9.2.0 with Starlette/FastAPI `TestClient` |
| Data access | Hand-written SQL only |

## Project Structure

```text
app/
  main.py              FastAPI application factory
  routes/matches.py    Health and matching endpoints
  repository.py        Raw SQL data access
  matching.py          Scoring, explanations, and ranking
  domain.py            Plain domain dataclasses
  schemas.py           API response models
  seed_data.py         Canonical 15 candidates / 6 jobs
  seed.py              Repeatable seed CLI
db/
  schema.sql           Part 1 schema
scripts/
  init_sql_detective.py
  run_sql_detective.py
sql_detective/
  schema.sql           Part 2 supplied schema
  seed.sql             Part 2 supplied seed data
sql_detective.sql      All five Part 2 queries
tests/                 Scoring, API, seed, and SQL tests
TECHNICAL_NOTES.md     Detailed design decisions and trade-offs
```

## Setup and Run

### Prerequisites

- Python 3.14 installed
- A shell in the repository root

### 1. Create and activate a virtual environment

```bash
python -m venv .venv
```

Windows PowerShell:

```powershell
.\.venv\Scripts\Activate.ps1
```

macOS/Linux:

```bash
source .venv/bin/activate
```

### 2. Install dependencies

For runtime only:

```bash
python -m pip install -r requirements.txt
```

For runtime plus tests:

```bash
python -m pip install -r requirements-dev.txt
```

### 3. Seed the database

```bash
python -m app.seed
```

This rebuilds the schema and inserts the canonical dataset into `db/recruiterflow.db`. Re-running it recreates the data without duplicating records. Use `--db path/to/file.db` to target another SQLite file, or set `RECRUITERFLOW_DB`.

### 4. Start the API

```bash
python -m uvicorn app.main:app --reload
```

The API is available at `http://127.0.0.1:8000`. Interactive documentation is at `/docs`, and the health check is at `/health`.

The app also creates and seeds the default database automatically if it does not exist.

### 5. Run tests

```bash
python -m pytest -q
```

### SQL Detective

Initialise the separate Part 2 dataset and run all five queries:

```bash
python -m scripts.init_sql_detective
python -m scripts.run_sql_detective
```

## API Endpoints

| Method | Path | Description |
|---|---|---|
| GET | `/health` | Database status and seeded candidate/job counts |
| GET | `/jobs/{id}/matches` | Candidates ranked for a job |
| GET | `/candidates/{id}/matches` | Jobs ranked for a candidate |

### Examples

```bash
curl http://127.0.0.1:8000/health
curl http://127.0.0.1:8000/jobs/1/matches
curl http://127.0.0.1:8000/candidates/1/matches
```

A job-match response contains the job, scoring weights, and a ranked list. Each result includes the candidate identity, score, component breakdown, matched/missing skills, matched culture keywords, and an explanation:

```json
{
  "job": { "id": 1, "title": "Backend Detective" },
  "count": 15,
  "scoring": {
    "scale": "0-100",
    "weights": {
      "skills": 55.0,
      "experience": 25.0,
      "availability": 10.0,
      "culture": 10.0
    }
  },
  "results": [
    {
      "rank": 1,
      "candidate_id": 1,
      "candidate_name": "Sherlock H.",
      "score": 95.0,
      "breakdown": {
        "skills": 55.0,
        "experience": 25.0,
        "availability": 10.0,
        "culture": 5.0
      },
      "matched_skills": ["deduction", "forensics", "pattern-recognition"],
      "missing_skills": [],
      "matched_culture_keywords": ["analytical"],
      "explanation": "Candidate matches 3/3 required skills (deduction, forensics, pattern-recognition); meets the 3-year minimum with 8 years; available immediately; culture fit on 1/2 keywords (analytical)."
    }
  ]
}
```

The candidate endpoint uses the same scoring engine in reverse:

```json
{
  "candidate": { "id": 1, "name": "Sherlock H." },
  "count": 6,
  "scoring": { "...": "..." },
  "results": [
    {
      "rank": 1,
      "job_id": 1,
      "job_title": "Backend Detective",
      "score": 95.0,
      "breakdown": { "...": "..." },
      "explanation": "Candidate matches 3/3 required skills ..."
    }
  ]
}
```

### Error Behaviour

| Condition | Response |
|---|---|
| Missing job or candidate ID | `404 Not Found` |
| Non-positive or non-integer ID | `422 Unprocessable Entity` |
| Empty candidate/job pool | `200 OK` with `count: 0` and `results: []` |
| Database query/connection error | `503 Service Unavailable` |

## Database Structure

The Part 1 schema is in `db/schema.sql` and uses foreign keys plus junction-table primary keys to prevent duplicate relationships.

| Table | Purpose |
|---|---|
| `candidates` | Name, years of experience, availability, quirk |
| `jobs` | Title, minimum experience, tagline |
| `skills` | Canonical skill names |
| `traits` | Canonical candidate traits |
| `culture_keywords` | Canonical job culture keywords |
| `candidate_skills` | Candidate ↔ skill relationship |
| `candidate_traits` | Candidate ↔ trait relationship |
| `job_skills` | Job ↔ required-skill relationship |
| `job_culture_keywords` | Job ↔ culture-keyword relationship |
| `culture_trait_affinities` | Explicit affinity map from culture keywords to traits |

The Part 2 SQL Detective dataset is intentionally separate and uses the supplied schema unchanged: `recruiters`, `job_postings`, `applicants`, and `interviews`.

## Matching Formula

Every candidate/job pair receives a score from **0 to 100**:

```text
score = 55 * skill_coverage
      + 25 * experience_fit
      + 10 * availability_fit
      + 10 * culture_fit
```

| Component | Weight | Calculation |
|---|---:|---|
| Skills | 55 | Matched required skills ÷ total required skills. Extra skills earn no bonus. |
| Experience | 25 | `1.0` when candidate years meet the minimum; otherwise candidate years ÷ minimum years. Surplus experience is not penalised. |
| Availability | 10 | Immediate = `1.0`, 2 weeks = `0.6`, Not looking = `0.2`. |
| Culture | 10 | Matched culture keywords ÷ job culture keywords, using the explicit `culture_trait_affinities` map. |

Results are sorted by score, then skill coverage, then experience fit, then a case-insensitive name/title tie-break, then numeric ID. Both endpoints use the same scoring function, so a candidate/job pair receives the same score in either direction.

`TECHNICAL_NOTES.md` contains the full rationale, scoring edge cases, and trade-offs.

## SQL Detective Challenge

`sql_detective.sql` contains the five required queries, each preceded by its question number:

1. Open job postings with their recruiter.
2. Final-stage applicant count per job posting.
3. People who applied to more than one posting, deduplicating identities with `LOWER(TRIM(email))` and falling back to applicant ID when email is missing.
4. Recruiters' Final-stage conversion rate, limited to recruiters with at least three Final interviews.
5. Bonus: top recruiter by passed Final placements per department using `ROW_NUMBER()`, with deterministic tie-breaking by recruiter name and ID.

The supplied schema and seed data live in `sql_detective/schema.sql` and `sql_detective/seed.sql`.

## Design Decisions

- **Raw SQL only.** Every application query is a static, hand-written SQL string; external values are bound parameters.
- **Normalised data model.** Skills, traits, and culture keywords are first-class entities, so matching never parses comma-separated text.
- **Explicit culture mapping.** Trait compatibility is stored in a reviewable table instead of relying on fuzzy string matching.
- **Soft availability signal.** "Not looking" is penalised but not excluded, preserving strong skill/experience matches.
- **No overqualification penalty.** Minimum experience is treated as a threshold, not a ceiling.
- **Deterministic output.** Stable tie-breakers make repeated requests return identical rankings.
- **Separate SQL challenge.** Part 2 uses its own schema and seed data so the assignment's supplied structure remains intact.

## Limitations

- Scoring runs in Python after loading the small dataset; a production-scale system would need pagination, pre-filtering, or SQL-side candidate reduction.
- The culture affinity map is a judgement call and intentionally contributes only 10% of the score.
- Availability and experience are soft signals; real recruiting systems may need hard knockout rules or recruiter overrides.
- The API has no authentication, rate limiting, write endpoints, or pagination.
- SQL Detective Q3 treats having an interview row as evidence that an applicant applied to that posting, because the supplied schema has no separate application table.
- SQL Detective Q5 only returns departments with at least one successful Final placement.

## AI Usage Disclosure

AI coding assistance was used to help interpret the assignment brief, scaffold the FastAPI/SQLite application, draft SQL queries and tests, and prepare documentation. The implementation, SQL results, API behaviour, and tests were run and validated locally.

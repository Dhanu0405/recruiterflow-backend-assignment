-- Recruiter Bot relational schema (raw SQL, no ORM).
-- Skills, traits and culture keywords are intentionally normalised so that
-- matching never has to parse comma-separated strings at query time.

PRAGMA foreign_keys = ON;

CREATE TABLE IF NOT EXISTS candidates (
    id               INTEGER PRIMARY KEY,
    name             TEXT    NOT NULL UNIQUE,
    experience_years INTEGER NOT NULL CHECK (experience_years >= 0),
    availability     TEXT    NOT NULL CHECK (availability IN ('Immediate', '2 weeks', 'Not looking')),
    quirk            TEXT    NOT NULL
);

CREATE TABLE IF NOT EXISTS jobs (
    id                  INTEGER PRIMARY KEY,
    title               TEXT    NOT NULL UNIQUE,
    min_experience_years INTEGER NOT NULL CHECK (min_experience_years >= 0),
    tagline             TEXT    NOT NULL
);

CREATE TABLE IF NOT EXISTS skills (
    id   INTEGER PRIMARY KEY,
    name TEXT    NOT NULL UNIQUE
);

CREATE TABLE IF NOT EXISTS traits (
    id   INTEGER PRIMARY KEY,
    name TEXT    NOT NULL UNIQUE
);

CREATE TABLE IF NOT EXISTS culture_keywords (
    id   INTEGER PRIMARY KEY,
    name TEXT    NOT NULL UNIQUE
);

CREATE TABLE IF NOT EXISTS candidate_skills (
    candidate_id INTEGER NOT NULL REFERENCES candidates(id) ON DELETE CASCADE,
    skill_id     INTEGER NOT NULL REFERENCES skills(id) ON DELETE CASCADE,
    PRIMARY KEY (candidate_id, skill_id)
);

CREATE TABLE IF NOT EXISTS candidate_traits (
    candidate_id INTEGER NOT NULL REFERENCES candidates(id) ON DELETE CASCADE,
    trait_id     INTEGER NOT NULL REFERENCES traits(id) ON DELETE CASCADE,
    PRIMARY KEY (candidate_id, trait_id)
);

CREATE TABLE IF NOT EXISTS job_skills (
    job_id   INTEGER NOT NULL REFERENCES jobs(id) ON DELETE CASCADE,
    skill_id INTEGER NOT NULL REFERENCES skills(id) ON DELETE CASCADE,
    PRIMARY KEY (job_id, skill_id)
);

CREATE TABLE IF NOT EXISTS job_culture_keywords (
    job_id     INTEGER NOT NULL REFERENCES jobs(id) ON DELETE CASCADE,
    keyword_id INTEGER NOT NULL REFERENCES culture_keywords(id) ON DELETE CASCADE,
    PRIMARY KEY (job_id, keyword_id)
);

-- Curated bridge between a job's culture keyword and a candidate trait.
-- This keeps the inference explicit and reviewable instead of relying on
-- fuzzy string matching at request time. Every row has equal weight (1.0).
CREATE TABLE IF NOT EXISTS culture_trait_affinities (
    keyword_id INTEGER NOT NULL REFERENCES culture_keywords(id) ON DELETE CASCADE,
    trait_id   INTEGER NOT NULL REFERENCES traits(id) ON DELETE CASCADE,
    PRIMARY KEY (keyword_id, trait_id)
);

CREATE INDEX IF NOT EXISTS idx_candidate_skills_skill ON candidate_skills(skill_id);
CREATE INDEX IF NOT EXISTS idx_candidate_traits_trait ON candidate_traits(trait_id);
CREATE INDEX IF NOT EXISTS idx_job_skills_skill ON job_skills(skill_id);
CREATE INDEX IF NOT EXISTS idx_job_culture_keywords_keyword ON job_culture_keywords(keyword_id);

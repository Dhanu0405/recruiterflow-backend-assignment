-- RecruiterFlow Backend Assignment - Part 2: SQL Detective Challenge
-- SQLite-compatible queries against the supplied hiring-ops dataset.
-- Setup data lives in sql_detective/schema.sql and sql_detective/seed.sql.

-- Question 1: List all currently open job postings, along with the name of
-- the recruiter who owns each one.
SELECT
    jp.id              AS job_posting_id,
    jp.title           AS job_title,
    jp.department,
    jp.opened_date,
    r.id               AS recruiter_id,
    r.name             AS recruiter_name
FROM job_postings AS jp
JOIN recruiters AS r
    ON r.id = jp.recruiter_id
WHERE jp.status = 'open'
ORDER BY jp.opened_date, jp.id;

-- Question 2: For each job posting, how many applicants reached the Final
-- interview stage? Count distinct people, because one person can have more
-- than one interview row for the same posting. LEFT JOIN keeps postings with
-- zero Final interviews.
SELECT
    jp.id                         AS job_posting_id,
    jp.title                      AS job_title,
    COUNT(DISTINCT i.applicant_id) AS final_stage_applicants
FROM job_postings AS jp
LEFT JOIN interviews AS i
    ON i.job_posting_id = jp.id
   AND i.stage = 'Final'
GROUP BY jp.id, jp.title
ORDER BY jp.id;

-- Question 3: Find every person who effectively applied to more than one job
-- posting. Identity is the case-insensitive, trimmed email address. Rows with
-- no email fall back to their applicant id so unrelated NULL emails are never
-- merged. Distinct job postings are counted so repeat interviews at one job
-- do not inflate the result.
WITH normalised_applicants AS (
    SELECT
        id,
        full_name,
        email,
        CASE
            WHEN email IS NOT NULL AND TRIM(email) <> ''
                THEN LOWER(TRIM(email))
            ELSE 'applicant-id:' || id
        END AS identity_key
    FROM applicants
),
identity_jobs AS (
    SELECT
        na.identity_key,
        MIN(na.full_name) AS full_name,
        MIN(na.email)     AS email,
        COUNT(DISTINCT i.job_posting_id) AS job_count
    FROM normalised_applicants AS na
    JOIN interviews AS i
        ON i.applicant_id = na.id
    GROUP BY na.identity_key
    HAVING COUNT(DISTINCT i.job_posting_id) > 1
)
SELECT
    ij.full_name,
    ij.email,
    ij.job_count,
    (
        SELECT GROUP_CONCAT(DISTINCT i2.job_posting_id)
        FROM normalised_applicants AS na2
        JOIN interviews AS i2
            ON i2.applicant_id = na2.id
        WHERE na2.identity_key = ij.identity_key
    ) AS job_posting_ids,
    (
        SELECT GROUP_CONCAT(DISTINCT jp.title)
        FROM normalised_applicants AS na3
        JOIN interviews AS i3
            ON i3.applicant_id = na3.id
        JOIN job_postings AS jp
            ON jp.id = i3.job_posting_id
        WHERE na3.identity_key = ij.identity_key
    ) AS job_titles
FROM identity_jobs AS ij
ORDER BY ij.full_name;

-- Question 4: For each recruiter, compute the Final-stage conversion rate
-- (passed / total Final-stage interviews), only for recruiters with at least
-- three Final-stage interviews. A pending/NULL outcome still counts in the
-- denominator because it was a Final-stage interview.
SELECT
    r.id AS recruiter_id,
    r.name AS recruiter_name,
    COUNT(*) AS final_interviews,
    SUM(CASE WHEN i.outcome = 'passed' THEN 1 ELSE 0 END) AS final_passes,
    ROUND(
        100.0 * SUM(CASE WHEN i.outcome = 'passed' THEN 1 ELSE 0 END) / COUNT(*),
        2
    ) AS conversion_rate_pct
FROM interviews AS i
JOIN job_postings AS jp
    ON jp.id = i.job_posting_id
JOIN recruiters AS r
    ON r.id = jp.recruiter_id
WHERE i.stage = 'Final'
GROUP BY r.id, r.name
HAVING COUNT(*) >= 3
ORDER BY conversion_rate_pct DESC, r.name;

-- Question 5 (Bonus): Using a window function, find the recruiter with the
-- most successful placements (passed at Final stage) per department.
-- Only departments with at least one successful placement are represented.
-- Ties are resolved deterministically by recruiter name, then recruiter id.
-- (Use RANK() instead of ROW_NUMBER() if co-winners should all be returned.)
WITH department_placements AS (
    SELECT
        jp.department,
        r.id   AS recruiter_id,
        r.name AS recruiter_name,
        COUNT(*) AS placements
    FROM interviews AS i
    JOIN job_postings AS jp
        ON jp.id = i.job_posting_id
    JOIN recruiters AS r
        ON r.id = jp.recruiter_id
    WHERE i.stage = 'Final'
      AND i.outcome = 'passed'
    GROUP BY jp.department, r.id, r.name
),
ranked AS (
    SELECT
        department,
        recruiter_id,
        recruiter_name,
        placements,
        ROW_NUMBER() OVER (
            PARTITION BY department
            ORDER BY placements DESC, recruiter_name ASC, recruiter_id ASC
        ) AS recruiter_rank
    FROM department_placements
)
SELECT
    department,
    recruiter_id,
    recruiter_name,
    placements
FROM ranked
WHERE recruiter_rank = 1
ORDER BY department;

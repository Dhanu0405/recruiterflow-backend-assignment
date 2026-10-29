from __future__ import annotations

import sqlite3
from contextlib import closing

from scripts.run_sql_detective import read_queries


def _rows(db_path, index: int):
    with closing(sqlite3.connect(db_path)) as conn:
        conn.row_factory = sqlite3.Row
        statement = read_queries()[index]
        return conn.execute(statement).fetchall()


def test_query_file_contains_five_numbered_questions():
    from pathlib import Path

    text = (
        Path(__file__).resolve().parent.parent / "sql_detective.sql"
    ).read_text(encoding="utf-8")
    for question in range(1, 6):
        assert f"Question {question}" in text
    assert len(read_queries()) == 5


def test_question_1_open_postings_with_recruiters(sql_db_path):
    rows = _rows(sql_db_path, 0)

    assert [row["job_posting_id"] for row in rows] == [1, 2, 5, 4]
    assert {row["recruiter_name"] for row in rows} == {
        "Priya Shah",
        "Daniel Ortiz",
        "Wei Zhang",
    }
    assert all(row["job_title"] for row in rows)


def test_question_2_final_stage_applicants_per_posting(sql_db_path):
    rows = _rows(sql_db_path, 1)

    actual = {
        row["job_posting_id"]: row["final_stage_applicants"] for row in rows
    }
    assert actual == {1: 2, 2: 2, 3: 1, 4: 2, 5: 0, 6: 0, 7: 2}


def test_question_3_deduplicates_case_insensitive_emails(sql_db_path):
    rows = _rows(sql_db_path, 2)

    people = {row["full_name"]: row for row in rows}
    assert set(people) == {"Ananya Rao", "Ben Turner", "Elena Popescu"}
    assert all(row["job_count"] == 2 for row in rows)

    # The two Ananya applicant rows must collapse to one result with two jobs.
    assert people["Ananya Rao"]["job_count"] == 2
    assert {
        int(value) for value in people["Ananya Rao"]["job_posting_ids"].split(",")
    } == {1, 4}
    assert {
        int(value) for value in people["Ben Turner"]["job_posting_ids"].split(",")
    } == {1, 3}
    assert {
        int(value) for value in people["Elena Popescu"]["job_posting_ids"].split(",")
    } == {2, 7}


def test_question_4_conversion_rate_with_minimum_volume(sql_db_path):
    rows = _rows(sql_db_path, 3)

    actual = {
        row["recruiter_name"]: (
            row["final_interviews"],
            row["final_passes"],
            row["conversion_rate_pct"],
        )
        for row in rows
    }
    assert actual == {
        "Priya Shah": (4, 3, 75.0),
        "Daniel Ortiz": (4, 2, 50.0),
    }


def test_question_5_window_function_top_recruiter_per_department(sql_db_path):
    rows = _rows(sql_db_path, 4)

    actual = {row["department"]: row for row in rows}
    assert set(actual) == {"Data", "Engineering"}
    assert actual["Engineering"]["recruiter_name"] == "Priya Shah"
    assert actual["Engineering"]["placements"] == 3
    assert actual["Data"]["recruiter_name"] == "Fatima Al-Sayed"
    assert actual["Data"]["placements"] == 1

    # ROW_NUMBER guarantees exactly one winner per represented department.
    assert len(rows) == len({row["department"] for row in rows})


def test_question_5_ties_break_deterministically_by_name(sql_db_path):
    with closing(sqlite3.connect(sql_db_path)) as conn:
        conn.row_factory = sqlite3.Row
        # Give Daniel a third Engineering placement so he ties Priya at 3.
        conn.execute(
            """
            INSERT INTO interviews
                (id, applicant_id, job_posting_id, stage, scheduled_date, outcome)
            VALUES (25, 7, 7, 'Final', '2026-03-01', 'passed')
            """
        )
        conn.commit()
        rows = conn.execute(read_queries()[4]).fetchall()

    engineering = next(row for row in rows if row["department"] == "Engineering")
    assert engineering["recruiter_name"] == "Daniel Ortiz"
    assert engineering["placements"] == 3

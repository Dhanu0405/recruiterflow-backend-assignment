from __future__ import annotations

from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from app.main import create_app
from app.seed import build_database


def test_health_check(client):
    response = client.get("/health")

    assert response.status_code == 200
    body = response.json()
    assert body == {
        "status": "ok",
        "database": "ok",
        "candidates": 15,
        "jobs": 6,
    }


def test_job_matches_returns_ranked_candidates(client):
    response = client.get("/jobs/1/matches")

    assert response.status_code == 200
    body = response.json()
    assert body["job"] == {"id": 1, "title": "Backend Detective"}
    assert body["count"] == 15
    assert len(body["results"]) == 15
    assert body["scoring"]["scale"] == "0-100"
    assert body["scoring"]["weights"] == {
        "skills": 55.0,
        "experience": 25.0,
        "availability": 10.0,
        "culture": 10.0,
    }

    results = body["results"]
    assert [item["rank"] for item in results] == list(range(1, 16))
    assert len({item["candidate_id"] for item in results}) == 15
    assert [item["score"] for item in results] == sorted(
        (item["score"] for item in results), reverse=True
    )
    for item in results:
        assert 0 <= item["score"] <= 100
        assert item["candidate_name"]
        assert item["explanation"]
        assert item["breakdown"].keys() == {
            "skills",
            "experience",
            "availability",
            "culture",
        }
        assert item["score"] == pytest.approx(sum(item["breakdown"].values()), abs=0.05)

    top = results[0]
    assert top["candidate_id"] == 1
    assert top["candidate_name"] == "Sherlock H."
    assert top["score"] == 95.0
    assert set(top["matched_skills"]) == {
        "deduction",
        "pattern-recognition",
        "forensics",
    }
    assert top["missing_skills"] == []


def test_candidate_matches_returns_ranked_jobs(client):
    response = client.get("/candidates/1/matches")

    assert response.status_code == 200
    body = response.json()
    assert body["candidate"] == {"id": 1, "name": "Sherlock H."}
    assert body["count"] == 6
    assert len(body["results"]) == 6
    assert [item["rank"] for item in body["results"]] == list(range(1, 7))

    results = body["results"]
    assert [item["score"] for item in results] == sorted(
        (item["score"] for item in results), reverse=True
    )
    assert results[0]["job_id"] == 1
    assert results[0]["job_title"] == "Backend Detective"
    assert results[0]["score"] == 95.0
    assert len({item["job_id"] for item in results}) == 6
    for item in results:
        assert 0 <= item["score"] <= 100
        assert item["explanation"]


def test_same_request_returns_identical_payloads(client):
    first = client.get("/jobs/2/matches")
    second = client.get("/jobs/2/matches")

    assert first.status_code == second.status_code == 200
    assert first.json() == second.json()


@pytest.mark.parametrize("path", ["/jobs/999/matches", "/candidates/999/matches"])
def test_missing_ids_return_404(client, path):
    response = client.get(path)
    assert response.status_code == 404
    assert "not found" in response.json()["detail"].lower()


@pytest.mark.parametrize(
    "path",
    ["/jobs/0/matches", "/candidates/0/matches", "/jobs/abc/matches"],
)
def test_invalid_ids_return_422(client, path):
    response = client.get(path)
    assert response.status_code == 422


def test_empty_candidate_pool_returns_empty_ranking(client, db_conn):
    db_conn.execute("DELETE FROM candidates")
    db_conn.commit()

    response = client.get("/jobs/1/matches")

    assert response.status_code == 200
    body = response.json()
    assert body["count"] == 0
    assert body["results"] == []


def test_empty_job_pool_returns_empty_ranking(client, db_conn):
    db_conn.execute("DELETE FROM jobs")
    db_conn.commit()

    response = client.get("/candidates/1/matches")

    assert response.status_code == 200
    body = response.json()
    assert body["count"] == 0
    assert body["results"] == []


def test_database_query_error_returns_503(tmp_path: Path):
    path = tmp_path / "will-be-removed.db"
    build_database(path)
    app = create_app(path)
    path.unlink()

    with TestClient(app) as client:
        response = client.get("/jobs/1/matches")

    assert response.status_code == 503
    assert "database" in response.json()["detail"].lower()

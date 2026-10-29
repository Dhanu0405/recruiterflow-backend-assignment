from __future__ import annotations

from contextlib import closing
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from app.db import connect
from app.main import create_app
from app.seed import build_database
from scripts.init_sql_detective import init_sql_detective


@pytest.fixture()
def db_path(tmp_path: Path) -> Path:
    path = tmp_path / "recruiterflow-test.db"
    build_database(path)
    return path


@pytest.fixture()
def client(db_path: Path):
    app = create_app(db_path)
    with TestClient(app) as test_client:
        yield test_client


@pytest.fixture()
def db_conn(db_path: Path):
    with closing(connect(db_path)) as conn:
        yield conn


@pytest.fixture()
def sql_db_path(tmp_path: Path) -> Path:
    return init_sql_detective(tmp_path / "sql-detective-test.db")

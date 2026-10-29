"""FastAPI application factory for Recruiter Bot."""

from __future__ import annotations

from pathlib import Path

from fastapi import FastAPI

from app.db import resolve_db_path, schema_exists
from app.routes import matches
from app.seed import build_database


def create_app(
    db_path: str | Path | None = None,
    *,
    initialize_if_missing: bool = True,
) -> FastAPI:
    path = resolve_db_path(db_path)

    app = FastAPI(
        title="Recruiter Bot",
        description=(
            "Backend matching service for RecruiterFlow. Scores and ranks "
            "candidates against jobs using deterministic, explainable rules."
        ),
        version="1.0.0",
    )
    app.state.db_path = path

    if initialize_if_missing and not schema_exists(path):
        build_database(path)

    app.include_router(matches.router)
    return app


app = create_app()

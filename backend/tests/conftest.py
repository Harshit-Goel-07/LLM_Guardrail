"""Shared pytest fixtures.

Forces an isolated, in-memory-ish SQLite DB and the offline TF-IDF backend so the
suite runs fast and fully offline (no model download needed in CI or locked-down
machines). The MiniLM path is exercised separately when the model is available.
"""
from __future__ import annotations

import os
import tempfile
from pathlib import Path

import pytest

# Configure environment BEFORE importing the app so settings pick it up.
_TMP_DB = Path(tempfile.gettempdir()) / "guardrail_test.db"
os.environ["GUARDRAIL_DATABASE_URL"] = f"sqlite:///{_TMP_DB.as_posix()}"
os.environ["GUARDRAIL_EMBEDDING_BACKEND"] = "tfidf"
os.environ["GUARDRAIL_LLM_PROVIDER"] = "mock"


@pytest.fixture(scope="session")
def engine():
    from app.config import get_settings
    from app.detection.engine import get_engine

    get_settings.cache_clear()
    get_engine.cache_clear()
    return get_engine()


@pytest.fixture()
def client():
    from fastapi.testclient import TestClient

    from app.db.session import init_db
    from app.main import app

    init_db()
    with TestClient(app) as c:
        yield c

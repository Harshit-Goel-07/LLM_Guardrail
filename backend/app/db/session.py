"""Engine / session management.

SQLite gets ``check_same_thread=False`` so the FastAPI threadpool can share the
connection pool; Postgres uses defaults. ``init_db`` creates tables on startup for
the zero-config demo path — Alembic migrations are the source of truth for real
deployments, but create_all keeps first-run frictionless.
"""
from __future__ import annotations

from collections.abc import Iterator

from sqlalchemy import create_engine
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session, sessionmaker

from ..config import get_settings
from .models import Base


def _make_engine() -> Engine:
    settings = get_settings()
    url = settings.database_url
    connect_args = {"check_same_thread": False} if url.startswith("sqlite") else {}
    return create_engine(url, connect_args=connect_args, pool_pre_ping=True, future=True)


engine: Engine = _make_engine()
SessionLocal = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)


def init_db() -> None:
    """Apply Alembic migrations (falls back to create_all on first run)."""
    from .migrate import run_migrations

    run_migrations(engine)


def get_session() -> Iterator[Session]:
    """FastAPI dependency that yields a scoped session."""
    session = SessionLocal()
    try:
        yield session
    finally:
        session.close()

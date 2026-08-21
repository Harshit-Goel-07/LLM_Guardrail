"""Run Alembic migrations programmatically at app startup."""
from __future__ import annotations

import logging
import os
from pathlib import Path

from alembic import command
from alembic.config import Config
from sqlalchemy import inspect, text
from sqlalchemy.engine import Engine

from ..config import BACKEND_DIR
from .models import Base

logger = logging.getLogger(__name__)


def _alembic_version_is_stamped(engine: Engine) -> bool:
    """Return True if alembic_version table exists and contains at least one row."""
    insp = inspect(engine)
    if "alembic_version" not in insp.get_table_names():
        return False
    with engine.connect() as conn:
        row = conn.execute(text("SELECT version_num FROM alembic_version LIMIT 1")).first()
        return row is not None


def _stamp_head(cfg: Config) -> None:
    """Stamp alembic_version to 'head' without running any migration steps."""
    try:
        command.stamp(cfg, "head")
        logger.info("Stamped Alembic version to head")
    except Exception as exc:  # noqa: BLE001
        logger.warning("Failed to stamp Alembic version: %s", exc)


def run_migrations(engine: Engine) -> None:
    """Apply Alembic migrations; fall back to create_all if Alembic is unavailable."""
    alembic_ini = BACKEND_DIR / "alembic.ini"
    if not alembic_ini.exists():
        logger.warning("alembic.ini not found; using create_all()")
        Base.metadata.create_all(bind=engine)
        return

    prev_cwd = Path.cwd()
    try:
        os.chdir(BACKEND_DIR)
        cfg = Config(str(alembic_ini))

        # If tables exist but alembic_version is not stamped (e.g. create_all was
        # used on a previous run), stamp to head instead of re-running migrations.
        insp = inspect(engine)
        tables_exist = "guard_events" in insp.get_table_names()
        stamped = _alembic_version_is_stamped(engine)

        if tables_exist and not stamped:
            logger.info("Tables exist but Alembic version not stamped; stamping to head")
            _stamp_head(cfg)
            return

        command.upgrade(cfg, "head")
        logger.info("Alembic migrations applied")
    except Exception as exc:  # noqa: BLE001 — keep demo path working
        logger.warning("Alembic upgrade failed (%s); falling back to create_all()", exc)
        Base.metadata.create_all(bind=engine)
        # Stamp so the next startup does not re-attempt the failed migration.
        try:
            _stamp_head(cfg)
        except Exception:  # noqa: BLE001
            pass
    finally:
        os.chdir(prev_cwd)

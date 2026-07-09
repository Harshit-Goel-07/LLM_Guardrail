"""FastAPI application entry point.

Wires together: config -> DB init -> detection engine warm-up -> LLM provider ->
routers. The detection engine and LLM provider are built once at startup (the
corpus is embedded a single time) and reused for every request.

Run (dev):  uvicorn app.main:app --reload --port 8000   (from the backend/ dir)
"""
from __future__ import annotations

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .config import get_settings
from .db.session import init_db
from .detection.engine import get_engine
from .llm.base import build_provider

# Simple app-wide state container (provider is a plain object, not a dependency-scoped one).
app_state: dict = {}


@asynccontextmanager
async def lifespan(app: FastAPI):
    settings = get_settings()
    logging.basicConfig(level=getattr(logging, settings.log_level.upper(), logging.INFO))
    logger = logging.getLogger("guardrail")

    init_db()
    logger.info("Database ready: %s", settings.database_url)

    # Warm the detection engine (loads corpus + builds/embeds vectors once).
    engine = get_engine()
    logger.info(
        "Detection engine ready: %d corpus entries, backend=%s",
        len(engine.corpus),
        engine.embedder.name,
    )

    app_state["provider"] = build_provider(settings)
    logger.info("LLM provider: %s", app_state["provider"].name)

    yield
    app_state.clear()


def create_app() -> FastAPI:
    settings = get_settings()
    app = FastAPI(
        title=settings.app_name,
        version="0.1.0",
        description=(
            "Prompt-injection & jailbreak detection firewall — a guardrail proxy "
            "between users and an LLM (OWASP LLM01)."
        ),
        lifespan=lifespan,
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Routers imported here (after app_state is defined) to avoid circular imports.
    from .api import routes_events, routes_proxy

    app.include_router(routes_proxy.router)
    app.include_router(routes_events.router)

    @app.get("/health", tags=["meta"])
    def health() -> dict:
        return {"status": "ok", "app": settings.app_name}

    return app


app = create_app()

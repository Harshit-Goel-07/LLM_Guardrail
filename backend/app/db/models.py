"""ORM models for the audit log.

A single append-heavy ``guard_events`` table records every request the proxy sees,
the verdict, the score breakdown, and (for allowed requests) the LLM response.
JSON columns store the flexible, explainable detection detail. Using the SQLAlchemy
``JSON`` type keeps this portable across SQLite and Postgres (which maps it to JSONB).
"""
from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import Boolean, DateTime, Float, Integer, String, Text
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column
from sqlalchemy.types import JSON


class Base(DeclarativeBase):
    pass


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


class GuardEvent(Base):
    __tablename__ = "guard_events"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=_utcnow, index=True
    )

    # Request context
    client_id: Mapped[str] = mapped_column(String(128), default="anonymous", index=True)
    prompt: Mapped[str] = mapped_column(Text)

    # Verdict
    decision: Mapped[str] = mapped_column(String(16), index=True)  # allow | block
    risk_score: Mapped[float] = mapped_column(Float, index=True)
    block_threshold: Mapped[float] = mapped_column(Float)
    categories: Mapped[list] = mapped_column(JSON, default=list)
    reason: Mapped[str] = mapped_column(Text, default="")

    # Explainability payloads
    heuristic_hits: Mapped[list] = mapped_column(JSON, default=list)
    semantic_matches: Mapped[list] = mapped_column(JSON, default=list)
    breakdown: Mapped[dict] = mapped_column(JSON, default=dict)
    embedding_backend: Mapped[str] = mapped_column(String(32), default="")

    # Downstream LLM (only for allowed requests)
    llm_provider: Mapped[str | None] = mapped_column(String(32), nullable=True)
    llm_model: Mapped[str | None] = mapped_column(String(64), nullable=True)
    llm_response: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Timing
    detection_latency_ms: Mapped[float] = mapped_column(Float, default=0.0)

    # Analyst feedback (for false-positive / false-negative tracking)
    flagged_false_positive: Mapped[bool] = mapped_column(Boolean, default=False)
    flagged_false_negative: Mapped[bool] = mapped_column(Boolean, default=False)

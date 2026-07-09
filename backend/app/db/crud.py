"""Data-access helpers for the audit log and dashboard stats."""
from __future__ import annotations

from datetime import datetime, timedelta, timezone

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from ..detection.schemas import Verdict
from ..llm.base import ChatResult
from .models import GuardEvent


def record_event(
    session: Session,
    *,
    prompt: str,
    verdict: Verdict,
    client_id: str = "anonymous",
    chat: ChatResult | None = None,
) -> GuardEvent:
    event = GuardEvent(
        client_id=client_id,
        prompt=prompt,
        decision=verdict.decision.value,
        risk_score=verdict.risk_score,
        block_threshold=verdict.block_threshold,
        categories=[c.value for c in verdict.categories],
        reason=verdict.reason,
        heuristic_hits=[h.model_dump(mode="json") for h in verdict.heuristic_hits],
        semantic_matches=[m.model_dump(mode="json") for m in verdict.semantic_matches],
        breakdown=verdict.breakdown.model_dump(mode="json"),
        embedding_backend=verdict.breakdown.embedding_backend,
        detection_latency_ms=verdict.latency_ms,
        llm_provider=chat.provider if chat else None,
        llm_model=chat.model if chat else None,
        llm_response=chat.content if chat else None,
    )
    session.add(event)
    session.commit()
    session.refresh(event)
    return event


def list_events(
    session: Session,
    *,
    limit: int = 100,
    offset: int = 0,
    decision: str | None = None,
) -> list[GuardEvent]:
    stmt = select(GuardEvent).order_by(GuardEvent.created_at.desc())
    if decision:
        stmt = stmt.where(GuardEvent.decision == decision)
    stmt = stmt.limit(limit).offset(offset)
    return list(session.scalars(stmt).all())


def get_event(session: Session, event_id: int) -> GuardEvent | None:
    return session.get(GuardEvent, event_id)


def flag_event(
    session: Session,
    event_id: int,
    *,
    false_positive: bool | None = None,
    false_negative: bool | None = None,
) -> GuardEvent | None:
    event = session.get(GuardEvent, event_id)
    if event is None:
        return None
    if false_positive is not None:
        event.flagged_false_positive = false_positive
    if false_negative is not None:
        event.flagged_false_negative = false_negative
    session.commit()
    session.refresh(event)
    return event


def stats(session: Session, *, window_hours: int = 24) -> dict:
    """Aggregate metrics for the dashboard summary cards and charts."""
    total = session.scalar(select(func.count(GuardEvent.id))) or 0
    blocked = (
        session.scalar(
            select(func.count(GuardEvent.id)).where(GuardEvent.decision == "block")
        )
        or 0
    )
    allowed = total - blocked
    false_positives = (
        session.scalar(
            select(func.count(GuardEvent.id)).where(
                GuardEvent.flagged_false_positive.is_(True)
            )
        )
        or 0
    )
    avg_latency = session.scalar(select(func.avg(GuardEvent.detection_latency_ms))) or 0.0
    avg_risk = session.scalar(select(func.avg(GuardEvent.risk_score))) or 0.0

    # Category counts (Python-side aggregation keeps this portable across DBs).
    cat_counts: dict[str, int] = {}
    for (cats,) in session.execute(select(GuardEvent.categories)):
        for c in cats or []:
            cat_counts[c] = cat_counts.get(c, 0) + 1

    # Risk-score histogram (10 buckets of width 10).
    histogram = [0] * 10
    for (score,) in session.execute(select(GuardEvent.risk_score)):
        bucket = min(9, int((score or 0) // 10))
        histogram[bucket] += 1

    # Time series over the window (per-hour blocked/allowed).
    since = datetime.now(timezone.utc) - timedelta(hours=window_hours)
    timeline: dict[str, dict[str, int]] = {}
    rows = session.execute(
        select(GuardEvent.created_at, GuardEvent.decision).where(
            GuardEvent.created_at >= since
        )
    )
    for created_at, decision in rows:
        hour = created_at.strftime("%Y-%m-%d %H:00")
        entry = timeline.setdefault(hour, {"allow": 0, "block": 0})
        entry[decision] = entry.get(decision, 0) + 1

    return {
        "total": total,
        "blocked": blocked,
        "allowed": allowed,
        "block_rate": round((blocked / total) * 100, 2) if total else 0.0,
        "false_positives": false_positives,
        "false_positive_rate": round((false_positives / blocked) * 100, 2)
        if blocked
        else 0.0,
        "avg_detection_latency_ms": round(float(avg_latency), 2),
        "avg_risk_score": round(float(avg_risk), 2),
        "category_counts": cat_counts,
        "risk_histogram": histogram,
        "timeline": [
            {"hour": h, **timeline[h]} for h in sorted(timeline.keys())
        ],
    }

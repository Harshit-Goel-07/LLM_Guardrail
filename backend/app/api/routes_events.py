"""Dashboard data endpoints: audit-log listing, stats, and analyst feedback."""
from __future__ import annotations

from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy.orm import Session

from ..db import crud
from ..db.session import get_session

router = APIRouter(prefix="/api", tags=["dashboard"])


class EventOut(BaseModel):
    id: int
    created_at: datetime
    client_id: str
    prompt: str
    decision: str
    risk_score: float
    block_threshold: float
    categories: list[str]
    reason: str
    heuristic_hits: list[dict]
    semantic_matches: list[dict]
    breakdown: dict
    embedding_backend: str
    llm_provider: str | None
    llm_model: str | None
    llm_response: str | None
    detection_latency_ms: float
    flagged_false_positive: bool
    flagged_false_negative: bool

    model_config = {"from_attributes": True}


class FlagRequest(BaseModel):
    false_positive: bool | None = None
    false_negative: bool | None = None


@router.get("/events", response_model=list[EventOut])
def get_events(
    limit: int = Query(100, ge=1, le=500),
    offset: int = Query(0, ge=0),
    decision: str | None = Query(None, pattern="^(allow|block)$"),
    session: Session = Depends(get_session),
) -> list[EventOut]:
    events = crud.list_events(session, limit=limit, offset=offset, decision=decision)
    return [EventOut.model_validate(e) for e in events]


@router.get("/events/{event_id}", response_model=EventOut)
def get_single_event(
    event_id: int, session: Session = Depends(get_session)
) -> EventOut:
    event = crud.get_event(session, event_id)
    if event is None:
        raise HTTPException(status_code=404, detail="Event not found")
    return EventOut.model_validate(event)


@router.post("/events/{event_id}/flag", response_model=EventOut)
def flag(
    event_id: int, body: FlagRequest, session: Session = Depends(get_session)
) -> EventOut:
    event = crud.flag_event(
        session,
        event_id,
        false_positive=body.false_positive,
        false_negative=body.false_negative,
    )
    if event is None:
        raise HTTPException(status_code=404, detail="Event not found")
    return EventOut.model_validate(event)


@router.get("/stats")
def get_stats(
    window_hours: int = Query(24, ge=1, le=720),
    session: Session = Depends(get_session),
) -> dict:
    return crud.stats(session, window_hours=window_hours)

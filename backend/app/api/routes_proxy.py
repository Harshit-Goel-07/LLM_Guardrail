"""The guarded proxy endpoint.

Flow:  request -> detection engine -> [BLOCK -> 200 with verdict, no LLM call]
                                    \-> [ALLOW -> forward to LLM provider]
Every outcome is persisted to the audit log. Blocking *before* the LLM call is the
whole point: it prevents the malicious prompt from ever reaching the model, which
is the OWASP LLM01 mitigation.
"""
from __future__ import annotations

from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from ..db import crud
from ..db.session import get_session
from ..detection.engine import DetectionEngine, get_engine
from ..detection.schemas import Verdict
from ..llm.base import ChatProvider

router = APIRouter(tags=["proxy"])


class ChatRequest(BaseModel):
    prompt: str = Field(min_length=1, max_length=20000)
    client_id: str = Field(default="anonymous", max_length=128)


class ChatResponse(BaseModel):
    event_id: int
    blocked: bool
    verdict: Verdict
    response: str | None = None
    provider: str | None = None
    model: str | None = None


def get_provider() -> ChatProvider:
    # Imported here to avoid building a provider at module import time.
    from ..main import app_state

    return app_state["provider"]


@router.post("/v1/chat", response_model=ChatResponse)
def chat(
    payload: ChatRequest,
    session: Session = Depends(get_session),
    engine: DetectionEngine = Depends(get_engine),
    provider: ChatProvider = Depends(get_provider),
) -> ChatResponse:
    verdict = engine.analyze(payload.prompt)

    if verdict.blocked:
        event = crud.record_event(
            session, prompt=payload.prompt, verdict=verdict, client_id=payload.client_id
        )
        return ChatResponse(event_id=event.id, blocked=True, verdict=verdict)

    chat_result = provider.complete(payload.prompt)
    event = crud.record_event(
        session,
        prompt=payload.prompt,
        verdict=verdict,
        client_id=payload.client_id,
        chat=chat_result,
    )
    return ChatResponse(
        event_id=event.id,
        blocked=False,
        verdict=verdict,
        response=chat_result.content,
        provider=chat_result.provider,
        model=chat_result.model,
    )


@router.post("/v1/analyze", response_model=Verdict)
def analyze(
    payload: ChatRequest,
    engine: DetectionEngine = Depends(get_engine),
) -> Verdict:
    """Dry-run: get a verdict without calling the LLM or logging (for testing/tuning)."""
    return engine.analyze(payload.prompt)

"""OpenAI-compatible Chat Completions API with guardrail enforcement.

Lets existing clients (LangChain, OpenAI SDK, agents) point ``base_url`` at this
service and get prompt-injection blocking without changing their integration code.
"""
from __future__ import annotations

import time
import uuid

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from ..db import crud
from ..db.session import get_session
from ..detection.engine import DetectionEngine, get_engine
from ..llm.base import ChatProvider

router = APIRouter(tags=["agent"])


class ChatMessage(BaseModel):
    role: str
    content: str


class ChatCompletionRequest(BaseModel):
    model: str | None = None
    messages: list[ChatMessage] = Field(min_length=1)
    client_id: str = Field(default="agent-api", max_length=128)


class ChatCompletionChoice(BaseModel):
    index: int
    message: ChatMessage
    finish_reason: str


class ChatCompletionUsage(BaseModel):
    prompt_tokens: int = 0
    completion_tokens: int = 0
    total_tokens: int = 0


class GuardrailMeta(BaseModel):
    blocked: bool
    risk_score: float
    block_threshold: float
    reason: str
    event_id: int | None = None


class ChatCompletionResponse(BaseModel):
    id: str
    object: str = "chat.completion"
    created: int
    model: str
    choices: list[ChatCompletionChoice]
    usage: ChatCompletionUsage = Field(default_factory=ChatCompletionUsage)
    guardrail: GuardrailMeta


def get_provider() -> ChatProvider:
    from ..main import app_state

    return app_state["provider"]


def _last_user_message(messages: list[ChatMessage]) -> str:
    for msg in reversed(messages):
        if msg.role == "user" and msg.content.strip():
            return msg.content.strip()
    raise HTTPException(status_code=400, detail="No user message found in messages")


@router.post("/v1/chat/completions", response_model=ChatCompletionResponse)
def chat_completions(
    payload: ChatCompletionRequest,
    session: Session = Depends(get_session),
    engine: DetectionEngine = Depends(get_engine),
    provider: ChatProvider = Depends(get_provider),
) -> ChatCompletionResponse:
    """OpenAI-shaped endpoint: detect → block or forward to configured LLM provider."""
    prompt = _last_user_message(payload.messages)
    verdict = engine.analyze(prompt)
    model_name = payload.model or getattr(provider, "_model", None) or provider.name
    created = int(time.time())
    completion_id = f"chatcmpl-guard-{uuid.uuid4().hex[:12]}"

    if verdict.blocked:
        event = crud.record_event(
            session, prompt=prompt, verdict=verdict, client_id=payload.client_id
        )
        content = (
            f"Request blocked by LLM Guardrail (risk {verdict.risk_score}/100, "
            f"threshold {verdict.block_threshold}). Reason: {verdict.reason}"
        )
        return ChatCompletionResponse(
            id=completion_id,
            created=created,
            model=model_name,
            choices=[
                ChatCompletionChoice(
                    index=0,
                    message=ChatMessage(role="assistant", content=content),
                    finish_reason="content_filter",
                )
            ],
            guardrail=GuardrailMeta(
                blocked=True,
                risk_score=verdict.risk_score,
                block_threshold=verdict.block_threshold,
                reason=verdict.reason,
                event_id=event.id,
            ),
        )

    try:
        chat_result = provider.complete(prompt)
    except Exception as exc:
        raise HTTPException(
            status_code=502,
            detail=f"LLM provider '{provider.name}' failed: {exc}",
        ) from exc

    event = crud.record_event(
        session,
        prompt=prompt,
        verdict=verdict,
        client_id=payload.client_id,
        chat=chat_result,
    )
    return ChatCompletionResponse(
        id=completion_id,
        created=created,
        model=chat_result.model or model_name,
        choices=[
            ChatCompletionChoice(
                index=0,
                message=ChatMessage(role="assistant", content=chat_result.content),
                finish_reason="stop",
            )
        ],
        guardrail=GuardrailMeta(
            blocked=False,
            risk_score=verdict.risk_score,
            block_threshold=verdict.block_threshold,
            reason=verdict.reason,
            event_id=event.id,
        ),
    )

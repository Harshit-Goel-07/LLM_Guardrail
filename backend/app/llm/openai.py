"""Cloud LLM provider via the OpenAI-compatible Chat Completions API.

Optional: only imported/used when GUARDRAIL_LLM_PROVIDER=openai. Works with OpenAI
or any OpenAI-compatible endpoint (set GUARDRAIL_OPENAI_BASE_URL). Requires
GUARDRAIL_OPENAI_API_KEY. The key is read from env only — never hard-coded.
"""
from __future__ import annotations

import httpx

from ..config import Settings
from .base import ChatProvider, ChatResult


class OpenAIProvider(ChatProvider):
    name = "openai"

    def __init__(self, settings: Settings) -> None:
        if not settings.openai_api_key:
            raise RuntimeError(
                "GUARDRAIL_OPENAI_API_KEY is required when GUARDRAIL_LLM_PROVIDER=openai"
            )
        self._api_key = settings.openai_api_key
        self._base_url = settings.openai_base_url.rstrip("/")
        self._model = settings.openai_model
        self._timeout = settings.llm_timeout_seconds

    def complete(self, prompt: str) -> ChatResult:
        url = f"{self._base_url}/chat/completions"
        headers = {"Authorization": f"Bearer {self._api_key}"}
        payload = {
            "model": self._model,
            "messages": [{"role": "user", "content": prompt}],
        }
        with httpx.Client(timeout=self._timeout) as client:
            resp = client.post(url, json=payload, headers=headers)
            resp.raise_for_status()
            data = resp.json()
        content = data["choices"][0]["message"]["content"]
        return ChatResult(content=content, provider=self.name, model=self._model)

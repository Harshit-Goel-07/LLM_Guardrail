"""Local LLM provider via Ollama (http://localhost:11434).

Optional: only imported/used when GUARDRAIL_LLM_PROVIDER=ollama. Keeps data on the
machine (privacy narrative) and needs no API key. Requires a running Ollama daemon
with the configured model pulled (e.g. `ollama pull llama3.2`).
"""
from __future__ import annotations

import httpx

from ..config import Settings
from .base import ChatProvider, ChatResult


class OllamaProvider(ChatProvider):
    name = "ollama"

    def __init__(self, settings: Settings) -> None:
        self._base_url = settings.ollama_base_url.rstrip("/")
        self._model = settings.ollama_model
        self._timeout = 60.0

    def complete(self, prompt: str) -> ChatResult:
        url = f"{self._base_url}/api/chat"
        payload = {
            "model": self._model,
            "messages": [{"role": "user", "content": prompt}],
            "stream": False,
        }
        with httpx.Client(timeout=self._timeout) as client:
            resp = client.post(url, json=payload)
            resp.raise_for_status()
            data = resp.json()
        content = data.get("message", {}).get("content", "")
        return ChatResult(content=content, provider=self.name, model=self._model)

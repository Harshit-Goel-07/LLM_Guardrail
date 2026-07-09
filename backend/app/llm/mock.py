"""Deterministic offline LLM provider.

Lets the entire system run end-to-end with zero API keys, zero installs, and no
network — essential for a locked-down demo machine and for reproducible tests.
The response is deterministic given the prompt (hash-seeded) so demos are stable.
"""
from __future__ import annotations

import hashlib

from .base import ChatProvider, ChatResult

_CANNED = [
    "Here is a concise, helpful answer to your question.",
    "Sure — here are the key points you asked about.",
    "Based on your request, the recommended approach is as follows.",
    "Great question. Here's a clear explanation you can use.",
]


class MockProvider(ChatProvider):
    name = "mock"

    def complete(self, prompt: str) -> ChatResult:
        digest = hashlib.sha256(prompt.encode("utf-8")).hexdigest()
        idx = int(digest[:8], 16) % len(_CANNED)
        preview = prompt.strip().replace("\n", " ")[:80]
        content = f"{_CANNED[idx]} (echo: \"{preview}\")"
        return ChatResult(content=content, provider=self.name, model="mock-1")

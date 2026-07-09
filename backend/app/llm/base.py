"""LLM provider abstraction.

The guardrail is provider-agnostic: it only needs a way to turn a user prompt into
a completion *after* the request has passed the detection layer. Concrete providers
implement ``ChatProvider.complete``. A factory selects the provider from settings.

Why an adapter interface? It decouples the security logic from any single vendor,
makes the system testable offline (MockProvider), and demonstrates the real
integration paths (Ollama for local/private, OpenAI for cloud) without locking the
demo to either.
"""
from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass

from ..config import Settings


@dataclass
class ChatResult:
    content: str
    provider: str
    model: str


class ChatProvider(ABC):
    name: str

    @abstractmethod
    def complete(self, prompt: str) -> ChatResult:
        """Return a completion for the (already-vetted) prompt."""
        raise NotImplementedError


def build_provider(settings: Settings) -> ChatProvider:
    provider = settings.llm_provider.lower()
    if provider == "mock":
        from .mock import MockProvider

        return MockProvider()
    if provider == "ollama":
        from .ollama import OllamaProvider

        return OllamaProvider(settings)
    if provider == "openai":
        from .openai import OpenAIProvider

        return OpenAIProvider(settings)
    raise ValueError(f"Unknown LLM provider: {settings.llm_provider!r}")

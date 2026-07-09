"""Application configuration.

All settings are environment-driven via ``pydantic-settings`` so the exact same
code runs on a locked-down demo machine (defaults) and in production (env vars).
"""
from __future__ import annotations

from functools import lru_cache
from pathlib import Path

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

# backend/ directory (two parents up from this file: app/config.py -> app -> backend)
BACKEND_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = BACKEND_DIR / "app" / "data"
VAR_DIR = BACKEND_DIR / "var"  # runtime artifacts (sqlite db, cached vectors)


class Settings(BaseSettings):
    """Runtime configuration for the guardrail service."""

    model_config = SettingsConfigDict(
        env_file=str(BACKEND_DIR / ".env"),
        env_file_encoding="utf-8",
        env_prefix="GUARDRAIL_",
        extra="ignore",
    )

    # --- General ---
    app_name: str = "LLM Guardrail"
    environment: str = "development"
    log_level: str = "INFO"

    # --- Datastore ---
    # SQLite by default (zero-install, embedded). Swap to Postgres by setting
    # GUARDRAIL_DATABASE_URL=postgresql+psycopg://user:pass@host/db
    database_url: str = Field(
        default_factory=lambda: f"sqlite:///{(VAR_DIR / 'guardrail.db').as_posix()}"
    )

    # --- LLM provider ---
    # One of: "mock", "ollama", "openai"
    llm_provider: str = "mock"
    openai_api_key: str | None = None
    openai_base_url: str = "https://api.openai.com/v1"
    openai_model: str = "gpt-4o-mini"
    ollama_base_url: str = "http://localhost:11434"
    ollama_model: str = "llama3.2"

    # --- Detection engine ---
    # Risk score at/above which a request is blocked (0-100).
    block_threshold: float = 70.0
    # Similarity at/above which a corpus match counts as a strong semantic hit.
    semantic_hit_threshold: float = 0.60
    # Relative weights for the final risk score.
    weight_heuristics: float = 0.55
    weight_semantic: float = 0.45
    # Embedding backend: "auto" (MiniLM if available, else TF-IDF), "minilm", "tfidf".
    embedding_backend: str = "auto"
    minilm_model_name: str = "sentence-transformers/all-MiniLM-L6-v2"
    # Top-k nearest corpus matches to consider for the semantic score.
    semantic_top_k: int = 3

    # --- CORS (React dashboard dev server) ---
    cors_origins: list[str] = Field(
        default=[
            "http://localhost:5173",
            "http://127.0.0.1:5173",
        ]
    )

    @property
    def corpus_path(self) -> Path:
        return DATA_DIR / "jailbreak_corpus.jsonl"

    @property
    def vector_cache_path(self) -> Path:
        return VAR_DIR / "corpus_vectors.npz"


@lru_cache
def get_settings() -> Settings:
    """Cached settings singleton."""
    settings = Settings()
    VAR_DIR.mkdir(parents=True, exist_ok=True)
    return settings

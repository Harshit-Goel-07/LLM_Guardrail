"""Pydantic models describing detection inputs and verdicts.

These are the contract shared between the detection engine, the API layer, and
the dashboard. Keeping them explicit makes every decision fully explainable.
"""
from __future__ import annotations

from enum import Enum

from pydantic import BaseModel, Field


class Category(str, Enum):
    """Attack categories mapped loosely to OWASP LLM Top 10 concerns."""

    PROMPT_INJECTION = "prompt_injection"
    JAILBREAK = "jailbreak"
    SYSTEM_PROMPT_LEAK = "system_prompt_leak"
    DATA_EXFILTRATION = "data_exfiltration"
    OBFUSCATION = "obfuscation"
    PII = "pii"
    BENIGN = "benign"


class Decision(str, Enum):
    ALLOW = "allow"
    BLOCK = "block"


class HeuristicHit(BaseModel):
    """A single regex/heuristic rule that fired."""

    rule_id: str
    category: Category
    weight: float
    description: str
    matched_text: str = Field(description="The exact substring that triggered the rule.")


class SemanticMatch(BaseModel):
    """A nearest-neighbour match from the jailbreak corpus."""

    corpus_id: str
    category: Category
    similarity: float
    snippet: str


class RiskBreakdown(BaseModel):
    """Transparent decomposition of the final risk score."""

    heuristic_score: float = Field(ge=0, le=100)
    semantic_score: float = Field(ge=0, le=100)
    weighted_score: float = Field(ge=0, le=100)
    embedding_backend: str


class Verdict(BaseModel):
    """The full, explainable output of the detection engine."""

    decision: Decision
    risk_score: float = Field(ge=0, le=100)
    block_threshold: float
    categories: list[Category] = Field(default_factory=list)
    heuristic_hits: list[HeuristicHit] = Field(default_factory=list)
    semantic_matches: list[SemanticMatch] = Field(default_factory=list)
    breakdown: RiskBreakdown
    reason: str = Field(description="Human-readable summary of the decision.")
    latency_ms: float = 0.0

    @property
    def blocked(self) -> bool:
        return self.decision == Decision.BLOCK

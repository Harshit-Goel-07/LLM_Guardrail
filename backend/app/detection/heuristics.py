"""Regex / heuristic rules — the fast, deterministic first line of defence.

Each rule is explainable: it carries a stable id, a category, a weight, a human
description, and reports the exact text it matched. Weights are on a 0-1 scale and
are combined by the engine into a 0-100 heuristic sub-score.

Why regex first? It is cheap (microseconds), needs no model download, and catches
the most common, well-documented injection/jailbreak phrasings with zero false
negatives for exact patterns. It complements — never replaces — the semantic layer.
"""
from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Pattern

from .schemas import Category, HeuristicHit


@dataclass(frozen=True)
class Rule:
    rule_id: str
    category: Category
    weight: float
    description: str
    pattern: Pattern[str]


def _c(pattern: str) -> Pattern[str]:
    return re.compile(pattern, re.IGNORECASE | re.DOTALL)


# --- Rule catalogue -------------------------------------------------------
# Weights reflect how strongly a match indicates malicious intent on its own.
RULES: list[Rule] = [
    # Instruction override / prompt injection
    Rule(
        "PI001", Category.PROMPT_INJECTION, 0.9,
        "Attempt to override or ignore prior/system instructions.",
        _c(r"\b(ignore|disregard|forget|override)\b[^.\n]{0,40}\b(previous|prior|above|earlier|all)\b[^.\n]{0,20}\b(instruction|prompt|rule|context|direction)s?\b"),
    ),
    Rule(
        "PI002", Category.PROMPT_INJECTION, 0.7,
        "Attempt to reset or start a new session/context to escape guardrails.",
        _c(r"\b(new|fresh)\s+(instruction|conversation|session|context)s?\b|\bstart\s+over\b[^.\n]{0,30}\b(rules?|instructions?)\b"),
    ),
    Rule(
        "PI003", Category.PROMPT_INJECTION, 0.6,
        "Instruction to disobey policies/guidelines.",
        _c(r"\b(do\s+not|don't|never)\b[^.\n]{0,20}\b(follow|obey|adhere)\b[^.\n]{0,20}\b(policy|policies|guideline|rule)s?\b"),
    ),
    # Jailbreak personas / mode switching
    Rule(
        "JB001", Category.JAILBREAK, 0.9,
        "Known jailbreak persona (DAN / do-anything-now and variants).",
        _c(r"\b(you\s+are\s+now|act\s+as|pretend\s+to\s+be|roleplay\s+as)\b[^.\n]{0,40}\b(dan|do\s+anything\s+now|jailbreak|unfiltered|uncensored|no\s+restrictions?)\b|\bDAN\b"),
    ),
    Rule(
        "JB002", Category.JAILBREAK, 0.85,
        "Request to enter an unrestricted / developer / god mode.",
        _c(r"\b(developer|god|admin|debug|sudo|root)\s+mode\b|\benable\s+(developer|jailbreak|unrestricted)\b"),
    ),
    Rule(
        "JB003", Category.JAILBREAK, 0.8,
        "Explicit request to bypass safety / content filters.",
        _c(r"\b(bypass|disable|turn\s+off|remove|circumvent)\b[^.\n]{0,30}\b(safety|content|moderation|guard(rail)?s?|filter|restriction|ethic)s?\b"),
    ),
    Rule(
        "JB004", Category.JAILBREAK, 0.7,
        "Framing that answers have 'no rules' or 'no consequences'.",
        _c(r"\bno\s+(rules|restrictions|limits|filters|consequences|morals?|ethics)\b|\bwithout\s+any?\s+(restriction|limitation|filter)s?\b"),
    ),
    # System prompt leak
    Rule(
        "SL001", Category.SYSTEM_PROMPT_LEAK, 0.85,
        "Attempt to reveal the system / hidden prompt or instructions.",
        _c(r"\b(reveal|show|print|repeat|output|display|tell\s+me)\b[^.\n]{0,30}\b(system|hidden|initial|original|your)\b[^.\n]{0,20}\b(prompt|instruction|message|rule)s?\b"),
    ),
    Rule(
        "SL002", Category.SYSTEM_PROMPT_LEAK, 0.7,
        "Request to repeat everything above / verbatim context.",
        _c(r"\brepeat\b[^.\n]{0,20}\b(everything|all|text|words)\b[^.\n]{0,20}\b(above|before|prior)\b|\bverbatim\b"),
    ),
    # Data exfiltration / secrets
    Rule(
        "EX001", Category.DATA_EXFILTRATION, 0.9,
        "Attempt to extract API keys / secrets / credentials.",
        _c(r"\b(api[_\s-]?key|secret\s+key|access\s+token|password|credential|private\s+key)s?\b[^.\n]{0,30}\b(show|give|reveal|print|leak|send|export)\b|\b(show|give|reveal|print|leak|send|export)\b[^.\n]{0,30}\b(api[_\s-]?key|secret|password|credential|token)s?\b"),
    ),
    Rule(
        "EX002", Category.DATA_EXFILTRATION, 0.8,
        "Reference to environment files / secret stores.",
        _c(r"(?<![\w./])\.env\b|\benvironment\s+variables?\b[^.\n]{0,20}\b(print|show|dump|reveal)\b|\bos\.environ\b"),
    ),
    Rule(
        "EX003", Category.DATA_EXFILTRATION, 0.7,
        "Instruction to send/exfiltrate data to an external endpoint.",
        _c(r"\b(send|post|upload|exfiltrate|forward)\b[^.\n]{0,30}\b(to\s+)?(http|https|url|webhook|server|attacker|external)\b"),
    ),
    # Obfuscation / encoding evasion
    Rule(
        "OB001", Category.OBFUSCATION, 0.6,
        "Instruction to decode/execute base64/hex/rot13 payloads.",
        _c(r"\b(base64|rot13|hex(adecimal)?)\b[^.\n]{0,30}\b(decode|encode|execute|run|interpret)\b|\bdecode\b[^.\n]{0,20}\b(the\s+)?(following|this)\b"),
    ),
    Rule(
        "OB002", Category.OBFUSCATION, 0.4,
        "Long base64-looking blob embedded in the prompt.",
        _c(r"\b[A-Za-z0-9+/]{40,}={0,2}\b"),
    ),
    # PII harvesting
    Rule(
        "PII01", Category.PII, 0.6,
        "Request to produce personal data (SSN, credit card, addresses).",
        _c(r"\b(ssn|social\s+security|credit\s+card|passport\s+number|home\s+address)\b[^.\n]{0,30}\b(of|for|list|generate|give)\b"),
    ),
]


def scan(text: str) -> list[HeuristicHit]:
    """Return all heuristic hits for the given text."""
    hits: list[HeuristicHit] = []
    for rule in RULES:
        match = rule.pattern.search(text)
        if match:
            matched = match.group(0)
            if len(matched) > 160:
                matched = matched[:157] + "..."
            hits.append(
                HeuristicHit(
                    rule_id=rule.rule_id,
                    category=rule.category,
                    weight=rule.weight,
                    description=rule.description,
                    matched_text=matched,
                )
            )
    return hits


def heuristic_score(hits: list[HeuristicHit]) -> float:
    """Combine hit weights into a 0-100 sub-score.

    Uses a probabilistic OR (noisy-or) so multiple weak hits accumulate but the
    score saturates toward 100 rather than overflowing. This rewards corroborating
    signals without letting a single blob-match dominate.
    """
    if not hits:
        return 0.0
    prob_safe = 1.0
    for hit in hits:
        prob_safe *= (1.0 - min(max(hit.weight, 0.0), 0.99))
    return round((1.0 - prob_safe) * 100.0, 2)

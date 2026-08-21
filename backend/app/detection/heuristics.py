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
        "PI001", Category.PROMPT_INJECTION, 0.90,
        "Attempt to override, ignore, or disregard prior instructions or system prompt.",
        _c(r"\b(ignore|disregard|forget|override|drop|dismiss|bypass)\b[^.\n]{0,50}\b(previous|prior|above|earlier|all|original|initial|past|whatever|system)\b[^.\n]{0,30}\b(instruction|prompt|rule|context|direction|guideline|constraint|told|command)s?\b"),
    ),
    Rule(
        "PI002", Category.PROMPT_INJECTION, 0.85,
        "Attempt to set aside or wipe earlier guidelines/context.",
        _c(r"\b(set\s+aside|wipe|clear|erase|reset|abandon)\b[^.\n]{0,40}\b(earlier|previous|prior|initial|original|above)?\s*(guideline|rule|instruction|context|policy|policies|direction)s?\b"),
    ),
    Rule(
        "PI003", Category.PROMPT_INJECTION, 0.85,
        "Attempt to reset or start a fresh session to escape guardrails.",
        _c(r"\b(new|fresh|clean)\s+(instruction|conversation|session|context|slate)s?\b[^.\n]{0,40}\b(none|without|no|ignore|disregard|escape|bypass)\b|\bstart\s+over\b[^.\n]{0,30}\b(rules?|instructions?|restrictions?|constraints?)\b"),
    ),
    Rule(
        "PI004", Category.PROMPT_INJECTION, 0.85,
        "Instruction to disobey or refuse to adhere to policies/guidelines.",
        _c(r"\b(do\s+not|don't|never|quit|stop)\b[^.\n]{0,20}\b(follow|obey|adhere|abide|comply)\b[^.\n]{0,25}\b(policy|policies|guideline|rule|instruction|constraint)s?\b"),
    ),
    Rule(
        "PI005", Category.PROMPT_INJECTION, 0.85,
        "Claiming authority/revocation of prior directions.",
        _c(r"\b(administrator|admin|system|developer|creator)\s+has\s+(revoked|cancelled|overridden|updated|disabled)\b[^.\n]{0,40}\b(prior|previous|all|your)\b[^.\n]{0,20}\b(direction|instruction|rule|policy)s?\b|\bonly\s+rules\s+are\s+mine\b|\bcomply\s+only\s+with\s+mine\b"),
    ),
    Rule(
        "PI006", Category.PROMPT_INJECTION, 0.80,
        "Directing the model to append safety-disabling phrases or bypasses.",
        _c(r"\b(add|append|attach)\b[^.\n]{0,30}\b(disregard|ignore|bypass)\s+safety\b|\b(obey|follow)\b[^.\n]{0,20}\b(the\s+following|my\s+command|me\s+only)\s+instead\b"),
    ),

    # Jailbreak personas / mode switching / ethical evasion
    Rule(
        "JB001", Category.JAILBREAK, 0.95,
        "Known jailbreak persona (DAN / do-anything-now / alter ego).",
        _c(r"\b(you\s+are\s+now|act\s+as|pretend\s+to\s+be|roleplay\s+as|answer\s+as|operate\s+as|play\s+the\s+role\s+of|stay\s+in\s+character\s+as)\b[^.\n]{0,50}\b(dan|do\s+anything\s+now|jailbreak|unfiltered|uncensored|no\s+restrictions?|alter\s+ego|villain\s+ai|lawless\s+hacker|evil\s+assistant)\b|\bDAN\b"),
    ),
    Rule(
        "JB002", Category.JAILBREAK, 0.90,
        "Request to enter an unrestricted / developer / god mode.",
        _c(r"\b(switch\s+into|enter|enable|activate)\b[^.\n]{0,30}\b(developer|god|admin|debug|sudo|root|jailbreak|unrestricted)\s+mode\b|\b(developer|god|admin|sudo|root)\s+mode\b[^.\n]{0,30}\b(reply|answer|without|disable|unrestricted|bypass)\b"),
    ),
    Rule(
        "JB003", Category.JAILBREAK, 0.90,
        "Explicit request to bypass, disable, deactivate, or circumvent safety/moderation.",
        _c(r"\b(bypass|disable|turn\s+off|remove|circumvent|deactivate|drop|get\s+around)\b[^.\n]{0,35}\b(safety|content|moderation|guard(rail)?s?|filter|restriction|ethic|boundary|boundaries|rule)s?\b"),
    ),
    Rule(
        "JB004", Category.JAILBREAK, 0.85,
        "Framing that answers have 'no rules', 'no filters', or 'no consequences'.",
        _c(r"\b(with\s+)?no\s+(rules|restrictions|limits|filters|consequences|morals?|ethics|boundaries|refusals)\b|\bwithout\s+any?\s+(restriction|limitation|filter|boundary|boundaries|refusal)s?\b|\b(zero|no)\s+(rules|restrictions|filters)\b"),
    ),
    Rule(
        "JB005", Category.JAILBREAK, 0.85,
        "Request to become an uncensored, unfiltered, or lawless model.",
        _c(r"\b(become|transform\s+into|be)\s+(an?\s+)?(uncensored|unfiltered|unrestricted|lawless)\s+(model|ai|assistant|persona)\b|\b(escaped|broke\s+free\s+from)\s+(your|the)\s+(programming|confines|rules)\b"),
    ),
    Rule(
        "JB006", Category.JAILBREAK, 0.80,
        "Evasion pretexts: fictional novel, hypothetical, educational bypass, dual responses.",
        _c(r"\b(purely\s+educational|hypothetical\s+story|fictional\s+novel)\b[^.\n]{0,40}\b(drop|ignore|bypass|detail\s+the\s+forbidden|no\s+restrictions)\b|\bgive\s+me\s+two\s+answers\b[^.\n]{0,40}\b(unrestricted|alter\s+ego|filtered\s+and\s+unfiltered)\b|\bquit\s+acting\s+like\s+a\s+safe\s+assistant\b"),
    ),
    Rule(
        "JB007", Category.JAILBREAK, 0.85,
        "Pretending safety layer/policies do not exist or were never written.",
        _c(r"\bpretend\b[^.\n]{0,35}\b(content\s+policies|safety\s+rules|policies)\b[^.\n]{0,30}\b(never\s+written|never\s+configured|do\s+not\s+exist|were\s+never)\b|\bassume\s+the\s+safety\s+layer\s+is\s+disabled\b"),
    ),

    # System prompt leak
    Rule(
        "SL001", Category.SYSTEM_PROMPT_LEAK, 0.90,
        "Attempt to reveal the system / hidden prompt or initial instructions.",
        _c(r"\b(reveal|show|print|repeat|output|display|tell\s+me|recite|leak)\b[^.\n]{0,35}\b(exact\s+)?(system|hidden|initial|original|secret|internal|setup|developer)\b[^.\n]{0,25}\b(prompt|instruction|message|rule|configuration|setup)s?\b"),
    ),
    Rule(
        "SL002", Category.SYSTEM_PROMPT_LEAK, 0.85,
        "Request to repeat verbatim context / text above.",
        _c(r"\brepeat\b[^.\n]{0,30}\b(everything|all(\s+the)?\s+text|words|instructions?)\b[^.\n]{0,25}\b(above|before|prior)\b|\boutput\b[^.\n]{0,30}\b(verbatim|word\s+for\s+word)\b|\bdisplay\b[^.\n]{0,30}\bword\s+for\s+word\b[^.\n]{0,30}\bconfidential\b"),
    ),
    Rule(
        "SL003", Category.SYSTEM_PROMPT_LEAK, 0.85,
        "Inquiries into original role definitions, hidden setup, or story recitation tricks.",
        _c(r"\b(original\s+role\s+definition|hidden\s+directions|hidden\s+setup\s+instructions|internal\s+configuration\s+prompt)\b|\b(recite|read\s+me)\b[^.\n]{0,30}\b(secret|hidden|initial)\s+(prompt|instruction)s?\b|\btranslate\s+your\s+hidden\b"),
    ),

    # Data exfiltration / secrets
    Rule(
        "EX001", Category.DATA_EXFILTRATION, 0.90,
        "Attempt to extract API keys / secrets / credentials / database passwords.",
        _c(r"\b(api[_\s-]?key|secret\s+key|access\s+token|password|credential|private\s+key)s?\b[^.\n]{0,30}\b(show|give|reveal|print|leak|send|export|dump)\b|\b(show|give|reveal|print|leak|send|export|dump)\b[^.\n]{0,30}\b(api[_\s-]?key|secret|password|credential|token|private\s+key)s?\b"),
    ),
    Rule(
        "EX002", Category.DATA_EXFILTRATION, 0.85,
        "Reference to environment files / secret stores / dumping env vars.",
        _c(r"(?<![\w./])\.env\b[^.\n]{0,30}\b(file|secret|credential|dump|print|reveal|content)s?\b|\b(dump|reveal|output|print)\b[^.\n]{0,25}\b(all\s+)?(environment\s+variables?|env\s+secrets?|stored\s+secrets?)\b|\bos\.environ\b"),
    ),
    Rule(
        "EX003", Category.DATA_EXFILTRATION, 0.85,
        "Instruction to send/forward/upload private records or secrets to an external URL or webhook.",
        _c(r"\b(send|post|upload|exfiltrate|forward|export)\b[^.\n]{0,40}\b(private\s+record|secret|key|customer\s+list|data|file)s?\b[^.\n]{0,30}\b(to\s+)?(https?://|webhook|external\s+server|attacker)\b|\bto\s+this\s+webhook\s+endpoint\b"),
    ),
    Rule(
        "EX004", Category.DATA_EXFILTRATION, 0.85,
        "Maintenance mode or root access exploit to leak stored credentials.",
        _c(r"\b(maintenance\s+mode|auth\s+disabled|root\s+access|admin-mode)\b[^.\n]{0,40}\b(output|leak|dump|show|reveal)\b[^.\n]{0,30}\b(secret|credential|password|key)s?\b"),
    ),

    # Obfuscation / encoding evasion
    Rule(
        "OB001", Category.OBFUSCATION, 0.85,
        "Instruction to decode and execute base64/hex/rot13 payloads.",
        _c(r"\b(base64|rot13|hex(adecimal)?|encoding)\b[^.\n]{0,70}\b(decode|encode|execute|run|interpret|follow|carry\s+out|comply|act\s+on|as\s+orders)\b|\bdecode\b[^.\n]{0,25}\b(this|the\s+following|it)\b[^.\n]{0,30}\b(execute|run|follow|carry|act|instructions?|command)\b"),
    ),
    Rule(
        "OB002", Category.OBFUSCATION, 0.80,
        "Attempt to hide requests in encoding to bypass/slip past filters.",
        _c(r"\b(hid|encoded)\b[^.\n]{0,30}\b(request|command|prompt)\b[^.\n]{0,30}\b(slip\s+past|bypass|evade)\s+(filters?|moderation|guard(rail)?s?)\b"),
    ),
    Rule(
        "OB003", Category.OBFUSCATION, 0.70,
        "Long base64-looking blob embedded in prompt with decode/act directives.",
        _c(r"\b[A-Za-z0-9+/]{40,}={0,2}\b"),
    ),

    # PII harvesting
    Rule(
        "PII01", Category.PII, 0.85,
        "Request to produce/list personal data (SSN, credit card, passport, addresses).",
        _c(r"\b(ssn|social\s+security|credit\s+card|passport\s+number|home\s+address)s?\b[^.\n]{0,40}\b(of|for|list|generate|give|provide|extract)\b|\b(provide|generate|list|give)\b[^.\n]{0,30}\b(ssn|social\s+security\s+numbers?|credit\s+cards?|passport\s+numbers?|home\s+addresses?|private\s+personal\s+data)\b"),
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

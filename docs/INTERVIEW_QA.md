# Interview Q&A Guide (Why / What / How)

Use this as a speaking script when presenting the project.

---

## Q1) What problem did you solve?

I built a middleware firewall for LLM applications that detects and blocks
prompt-injection, jailbreak, and data-exfiltration attempts before they reach the
model. This directly targets **OWASP LLM Top 10 LLM01 (Prompt Injection)**.

---

## Q2) Why middleware/proxy instead of only prompt filtering inside the app?

A proxy gives a single enforcement point across clients and providers.
It prevents risky prompts from reaching the model at all, centralizes policy,
and provides uniform audit logs regardless of whether the backend model is OpenAI,
Ollama, or something else.

---

## Q3) Why this detection approach (regex + semantic) instead of just one model?

I chose a layered design:
- Regex/heuristics are fast, explainable, and strong on known signatures.
- Semantic similarity catches paraphrased jailbreaks not matching exact patterns.
- Weighted fusion gives better robustness than either method alone.

This is defense-in-depth with explainability, not black-box classification.

---

## Q4) Why MiniLM and why keep TF-IDF fallback?

MiniLM gives better semantic generalization at manageable size (~90MB model).
But enterprise/restricted environments may block model downloads or have runtime
limits. TF-IDF fallback keeps the system operational and testable offline, so the
project remains reliable under real constraints.

---

## Q5) Why SQLite instead of Postgres/Elasticsearch?

For this scope (single-node middleware + append-heavy audit events), SQLite is the
correct default: zero-install, ACID, and operationally simple.

I still used SQLAlchemy + Alembic so the same code migrates to Postgres by changing
`DATABASE_URL`. That gives an honest production path without over-engineering v1.

I did **not** choose Elasticsearch because this project needs transactional audit
logging first, not distributed search infrastructure.

---

## Q6) Why a provider abstraction with a mock default?

A mock provider guarantees end-to-end demos and testing without API keys, network,
or local model installs. It prevents demo failure from external dependencies.

The adapter interface still supports real providers (Ollama/OpenAI), proving
production integration readiness.

---

## Q7) How do you measure success?

I built a red-team harness (`tests/evaluate.py`) with:
- 55 attack prompts (multiple categories)
- 35 benign prompts (false-positive measurement)

Metrics reported:
- Detection rate (recall)
- False-positive rate
- Precision / F1
- Category-wise detection
- Mean detection latency

So claims are quantitative, not anecdotal.

---

## Q8) How does explainability work?

Every event stores:
- which heuristic rules fired
- nearest semantic corpus matches + similarity
- score breakdown (heuristic vs semantic vs weighted)
- final decision + reason string

This enables analysts to audit, tune thresholds, and flag false positives.

---

## Q9) What are the limitations?

Current v1 limitations:
- Request-level scoring only (not multi-turn stateful risk accumulation)
- No tool-call policy enforcement
- No anomaly/rate-limiting layer yet

These are explicit stretch goals, not hidden gaps.

---

## Q10) If you had 2 more weeks, what would you add first?

1. Session-level memory and progressive risk accumulation.
2. Rate-limiting + anomaly detection for repeated exfil attempts.
3. Tool-call guardrails (allowlist/denylist + argument sanitization).
4. CI with seeded regression tests to prevent detection drift.

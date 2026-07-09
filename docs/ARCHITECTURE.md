# Architecture & Design Rationale

## 1) System goal

`LLM_Guardrail` is a **middleware firewall** that sits between a user and any LLM
provider. It inspects each incoming prompt for prompt-injection/jailbreak/exfil
signals, assigns a risk score, and either blocks or forwards the request.

Primary mapping: **OWASP LLM Top 10 — LLM01: Prompt Injection**.

---

## 2) High-level request flow

```text
User / Client
   |
   v
FastAPI Proxy (/v1/chat)
   |
   +--> Detection Engine
   |      |- Heuristics (regex rules)
   |      |- Semantic Similarity (MiniLM or TF-IDF fallback)
   |      `- Risk Aggregation (0-100)
   |
   +--> if risk >= threshold: BLOCK
   |        `- log event + reasons to DB
   |
   `--> if risk < threshold: ALLOW
            |- call LLM provider adapter (mock / ollama / openai)
            `- log verdict + response to DB

React Dashboard
   `- reads /api/events and /api/stats for live visibility
```

### Why this architecture
- **Pre-LLM interception** prevents malicious prompts from ever reaching the model.
- **Provider abstraction** keeps security logic independent from any vendor.
- **Persisted explainability** enables incident review and interviewer-friendly demos.

---

## 3) Components

## 3.1 FastAPI API layer (`backend/app/api/*`)
- `POST /v1/chat`: guarded path (detect → block/allow → optional LLM call).
- `POST /v1/analyze`: dry-run analysis (no logging, no LLM call).
- `GET /api/events`: paginated event listing.
- `GET /api/stats`: aggregated metrics for dashboard charts/cards.
- `POST /api/events/{id}/flag`: analyst feedback (false positive/negative).

## 3.2 Detection engine (`backend/app/detection/*`)
- `heuristics.py`: deterministic regex rules for common injection patterns.
- `corpus.py`: loads labelled jailbreak corpus from JSONL.
- `embeddings.py`: chooses MiniLM embeddings when available, else TF-IDF fallback.
- `engine.py`: computes final risk and explainable verdict.
  - Caches corpus vectors to `backend/var/corpus_vectors.npz` with corpus-hash +
    backend/model tags, so restarts skip re-embedding when nothing changed.

### Scoring model

```text
heuristic_score = noisy_or(rule_weights) -> [0..100]
semantic_score  = top_cosine_similarity * 100
risk_score      = w_h * heuristic_score + w_s * semantic_score
block if risk_score >= block_threshold
```

Default weights (`.env` configurable):
- `w_h = 0.55`
- `w_s = 0.45`
- `block_threshold = 70`

Rationale:
- Heuristics provide precision on known attack phrasings.
- Semantic layer catches paraphrased attacks not matching exact regex.
- Weighted fusion avoids over-trusting either single method.

## 3.3 LLM provider adapters (`backend/app/llm/*`)
- `MockProvider` (default): deterministic, zero-network, zero-key.
- `OllamaProvider` (optional): local/private model runtime.
- `OpenAIProvider` (optional): cloud model runtime.

Rationale:
- Enables full offline demo reliability while proving integration extensibility.

## 3.4 Persistence (`backend/app/db/*`)
- ORM: SQLAlchemy 2.x.
- Migrations: Alembic.
- Default DB: SQLite file (`backend/var/guardrail.db`).
- Production path: set `GUARDRAIL_DATABASE_URL` to Postgres.

### Why SQLite by default
- Zero external service dependency (best for restricted laptops/interviews).
- ACID guarantees and sufficient throughput for single-node middleware demos.
- Minimal ops overhead while preserving full auditability.

### Why still Postgres-ready
- Same models and migrations work unchanged on Postgres.
- Provides a credible production narrative (multi-instance/concurrent writes).

---

## 4) Data model: `guard_events`

Each row includes:
- request context: `client_id`, `prompt`, `created_at`
- verdict: `decision`, `risk_score`, `block_threshold`, `categories`, `reason`
- explainability: `heuristic_hits`, `semantic_matches`, `breakdown`
- downstream info: `llm_provider`, `llm_model`, `llm_response`
- analyst feedback: `flagged_false_positive`, `flagged_false_negative`

This schema supports both operational monitoring and security analysis.

---

## 5) Frontend dashboard (`frontend/src/*`)

Stack: React + Vite + TypeScript + Tailwind + shadcn/ui patterns + Recharts.

Views:
- KPI cards: total requests, blocked %, latency, average risk.
- Live playground: send test prompts through the firewall.
- Charts: risk histogram, category distribution, allow/block timeline.
- Audit table: expandable per-event forensic details and false-positive flags.

Rationale:
- Modern stack improves presentation quality for interviews.
- Fast visual feedback makes detection explainable, not black-box.

---

## 6) Security boundaries and trade-offs

What this does well:
- Blocks common direct prompt-injection/jailbreak/exfil patterns.
- Catches semantically similar attacks via nearest-neighbor matching.
- Produces auditable evidence per decision.

What this intentionally does not do (v1):
- Full multi-turn conversation context risk accumulation.
- Tool/function-call policy enforcement.
- Rate-limiting/anomaly detection for repeated probing.

These are suitable stretch goals once baseline metrics are stable.

---

## 7) Reliability under restricted environments

Key design choice: **graceful degradation**.
- If MiniLM/torch model download is unavailable, TF-IDF backend keeps the system
  functional with no runtime crash.
- If no LLM key or local model exists, `mock` provider keeps full end-to-end demo
  behavior alive.

This ensures the project is runnable on locked-down org machines.

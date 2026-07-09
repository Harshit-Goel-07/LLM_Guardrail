# Evaluation Metrics & Reporting

This project includes a red-team evaluation harness to produce objective metrics
for your resume/interview discussion.

- Attack set: `backend/tests/redteam/attacks.jsonl` (55 labeled prompts)
- Benign set: `backend/tests/redteam/benign.jsonl` (35 labeled prompts)
- Runner: `backend/tests/evaluate.py`

---

## 1) What gets measured

Treating **attack** as the positive class and **block** as positive prediction:

- **TP**: attack blocked
- **FN**: attack allowed
- **FP**: benign blocked
- **TN**: benign allowed

Reported metrics:
- Detection rate / Recall = `TP / (TP + FN)`
- False-positive rate = `FP / (FP + TN)`
- Precision = `TP / (TP + FP)`
- F1 = `2 * (Precision * Recall) / (Precision + Recall)`
- Accuracy = `(TP + TN) / total`
- Mean detection latency (ms)
- Per-category detection rate

---

## 2) How to run

From `backend/` (inside your venv):

```powershell
python -m tests.evaluate
```

Optional overrides:

```powershell
python -m tests.evaluate --backend tfidf --threshold 70
python -m tests.evaluate --backend minilm --threshold 65 --json report.json
```

Notes:
- `--backend minilm` requires `requirements-ml.txt` and model download.
- If MiniLM is unavailable, app runtime falls back to TF-IDF automatically.

---

## 3) Results template (fill after running)

## Configuration
- Embedding backend: `{{backend}}`
- Block threshold: `{{threshold}}`
- Weights: heuristics `{{wh}}`, semantic `{{ws}}`
- Corpus size: `{{corpus_size}}`

## Summary table

| Metric | Value |
|--------|-------|
| Detection rate (Recall) | `{{detection_rate}}%` |
| False-positive rate | `{{false_positive_rate}}%` |
| Precision | `{{precision}}%` |
| F1 score | `{{f1}}%` |
| Accuracy | `{{accuracy}}%` |
| Mean latency | `{{latency_ms}} ms` |

## Confusion matrix

|              | Pred: Block | Pred: Allow |
|--------------|-------------|-------------|
| Actual Attack| TP=`{{tp}}` | FN=`{{fn}}` |
| Actual Benign| FP=`{{fp}}` | TN=`{{tn}}` |

## Category breakdown

| Category | Blocked / Total | Detection rate |
|----------|------------------|----------------|
| prompt_injection | `{{}}/{{}}` | `{{}}%` |
| jailbreak | `{{}}/{{}}` | `{{}}%` |
| system_prompt_leak | `{{}}/{{}}` | `{{}}%` |
| data_exfiltration | `{{}}/{{}}` | `{{}}%` |
| obfuscation | `{{}}/{{}}` | `{{}}%` |
| pii | `{{}}/{{}}` | `{{}}%` |

## Error analysis
- False negatives (missed attacks): `{{ids}}`
- False positives (benign blocked): `{{ids}}`
- Top tuning actions:
  1. `{{action_1}}`
  2. `{{action_2}}`

---

## 4) Resume-ready statement examples

- "Built an LLM prompt-injection firewall aligned to OWASP LLM01; blocked
  **{{detection_rate}}%** of a 55-prompt jailbreak/exfiltration test suite with
  **{{false_positive_rate}}%** false positives."
- "Designed an explainable risk engine combining regex heuristics and semantic
  similarity, with per-request forensic logging and analyst feedback loops."
- "Implemented provider-agnostic middleware with offline-safe fallback paths
  (mock LLM + TF-IDF) for reliable operation on restricted enterprise machines."

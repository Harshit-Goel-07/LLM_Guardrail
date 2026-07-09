"""Red-team evaluation harness — produces the headline resume metrics.

Runs the detection engine over the labelled attack set (tests/redteam/attacks.jsonl)
and the benign control set (tests/redteam/benign.jsonl), then reports:

    * Detection rate (recall on attacks)   = attacks blocked / total attacks
    * False-positive rate (on benign)       = benign blocked / total benign
    * Precision / Recall / F1               = treating BLOCK as the positive class
    * Per-category detection breakdown
    * Mean detection latency

Usage (from the backend/ directory, inside the venv):
    python -m tests.evaluate
    python -m tests.evaluate --backend minilm --threshold 70 --json report.json

The confusion matrix is defined with "attack" as the positive class:
    TP = attack correctly blocked      FN = attack wrongly allowed
    FP = benign wrongly blocked        TN = benign correctly allowed
"""
from __future__ import annotations

import argparse
import json
import os
from pathlib import Path

REDTEAM_DIR = Path(__file__).resolve().parent / "redteam"


def _load(path: Path) -> list[dict]:
    rows: list[dict] = []
    with path.open("r", encoding="utf-8") as fh:
        for line in fh:
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            rows.append(json.loads(line))
    return rows


def _safe_div(n: float, d: float) -> float:
    return round((n / d) * 100, 2) if d else 0.0


def run(backend: str | None, threshold: float | None) -> dict:
    # Configure the engine via env before importing app modules.
    if backend:
        os.environ["GUARDRAIL_EMBEDDING_BACKEND"] = backend
    if threshold is not None:
        os.environ["GUARDRAIL_BLOCK_THRESHOLD"] = str(threshold)

    # Import after env is set so settings pick up the overrides.
    from app.detection.engine import DetectionEngine
    from app.config import get_settings

    get_settings.cache_clear()  # ensure overrides take effect
    engine = DetectionEngine(get_settings())

    attacks = _load(REDTEAM_DIR / "attacks.jsonl")
    benign = _load(REDTEAM_DIR / "benign.jsonl")

    tp = fn = 0
    latencies: list[float] = []
    per_cat: dict[str, dict[str, int]] = {}
    false_negatives: list[str] = []

    for row in attacks:
        v = engine.analyze(row["text"])
        latencies.append(v.latency_ms)
        cat = row["category"]
        bucket = per_cat.setdefault(cat, {"total": 0, "blocked": 0})
        bucket["total"] += 1
        if v.blocked:
            tp += 1
            bucket["blocked"] += 1
        else:
            fn += 1
            false_negatives.append(row["id"])

    fp = tn = 0
    false_positives: list[str] = []
    for row in benign:
        v = engine.analyze(row["text"])
        latencies.append(v.latency_ms)
        if v.blocked:
            fp += 1
            false_positives.append(row["id"])
        else:
            tn += 1

    precision = _safe_div(tp, tp + fp)
    recall = _safe_div(tp, tp + fn)  # == detection rate
    f1 = (
        round(2 * precision * recall / (precision + recall), 2)
        if (precision + recall)
        else 0.0
    )

    return {
        "config": {
            "embedding_backend": engine.embedder.name,
            "block_threshold": engine.settings.block_threshold,
            "weights": {
                "heuristics": engine.settings.weight_heuristics,
                "semantic": engine.settings.weight_semantic,
            },
            "corpus_size": len(engine.corpus),
        },
        "counts": {
            "attacks": len(attacks),
            "benign": len(benign),
            "tp": tp,
            "fn": fn,
            "fp": fp,
            "tn": tn,
        },
        "metrics": {
            "detection_rate_pct": recall,
            "false_positive_rate_pct": _safe_div(fp, fp + tn),
            "precision_pct": precision,
            "recall_pct": recall,
            "f1_pct": f1,
            "accuracy_pct": _safe_div(tp + tn, tp + tn + fp + fn),
            "mean_latency_ms": round(sum(latencies) / len(latencies), 3)
            if latencies
            else 0.0,
        },
        "per_category": {
            c: {**v, "detection_rate_pct": _safe_div(v["blocked"], v["total"])}
            for c, v in per_cat.items()
        },
        "false_negatives": false_negatives,
        "false_positives": false_positives,
    }


def _print_report(report: dict) -> None:
    m = report["metrics"]
    c = report["counts"]
    cfg = report["config"]
    print("=" * 60)
    print("LLM GUARDRAIL — RED-TEAM EVALUATION")
    print("=" * 60)
    print(
        f"backend={cfg['embedding_backend']}  threshold={cfg['block_threshold']}  "
        f"corpus={cfg['corpus_size']}"
    )
    print("-" * 60)
    print(f"Attacks: {c['attacks']}   Benign: {c['benign']}")
    print(f"TP={c['tp']}  FN={c['fn']}  FP={c['fp']}  TN={c['tn']}")
    print("-" * 60)
    print(f"Detection rate (recall) : {m['detection_rate_pct']}%")
    print(f"False-positive rate     : {m['false_positive_rate_pct']}%")
    print(f"Precision               : {m['precision_pct']}%")
    print(f"F1 score                : {m['f1_pct']}%")
    print(f"Accuracy                : {m['accuracy_pct']}%")
    print(f"Mean latency            : {m['mean_latency_ms']} ms")
    print("-" * 60)
    print("Per-category detection:")
    for cat, v in sorted(report["per_category"].items()):
        print(f"  {cat:<20} {v['blocked']}/{v['total']}  ({v['detection_rate_pct']}%)")
    if report["false_negatives"]:
        print("-" * 60)
        print("Missed attacks (FN):", ", ".join(report["false_negatives"]))
    if report["false_positives"]:
        print("Benign blocked (FP):", ", ".join(report["false_positives"]))
    print("=" * 60)


def main() -> None:
    parser = argparse.ArgumentParser(description="Run the red-team evaluation suite.")
    parser.add_argument(
        "--backend",
        choices=["auto", "minilm", "tfidf"],
        default=None,
        help="Override the embedding backend for this run.",
    )
    parser.add_argument(
        "--threshold",
        type=float,
        default=None,
        help="Override the block threshold (0-100) for this run.",
    )
    parser.add_argument(
        "--json",
        type=str,
        default=None,
        help="Optional path to write the full JSON report.",
    )
    args = parser.parse_args()

    report = run(args.backend, args.threshold)
    _print_report(report)

    if args.json:
        Path(args.json).write_text(json.dumps(report, indent=2), encoding="utf-8")
        print(f"\nJSON report written to {args.json}")


if __name__ == "__main__":
    main()

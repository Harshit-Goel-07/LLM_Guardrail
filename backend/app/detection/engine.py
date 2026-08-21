"""Detection engine: orchestrates heuristics + semantics into an explainable verdict.

Design (defense-in-depth):
    risk = w_h * heuristic_score + w_s * semantic_score      (both 0-100)
    decision = BLOCK if risk >= block_threshold else ALLOW

Both sub-scores and the exact signals that produced them are returned so the
dashboard and an interviewer can see *why* every request was allowed or blocked.
The engine is a singleton built once at startup (the corpus is embedded once and
cached), then reused per-request for low latency.
"""
from __future__ import annotations

import hashlib
import logging
import time
from functools import lru_cache

import numpy as np

from ..config import Settings, get_settings
from . import heuristics
from .corpus import CorpusEntry, load_corpus
from .embeddings import Embedder, build_embedder, cosine_similarity_matrix
from .schemas import (
    Category,
    Decision,
    RiskBreakdown,
    SemanticMatch,
    Verdict,
)

logger = logging.getLogger(__name__)


def _hash_texts(texts: list[str]) -> str:
    h = hashlib.sha256()
    for t in texts:
        h.update(t.encode("utf-8", errors="ignore"))
        h.update(b"\n")
    return h.hexdigest()


class DetectionEngine:
    def __init__(self, settings: Settings) -> None:
        self.settings = settings
        self.corpus: list[CorpusEntry] = load_corpus(settings.corpus_path)
        corpus_texts = [e.text for e in self.corpus]
        self._corpus_hash = _hash_texts(corpus_texts)
        self.embedder: Embedder = build_embedder(
            settings.embedding_backend,
            settings.minilm_model_name,
            corpus_texts,
        )
        # Precompute once and reuse via cache across restarts.
        self.corpus_vectors: np.ndarray = self._load_or_build_vectors(corpus_texts)

    def _cache_model_tag(self) -> str:
        if self.embedder.name == "minilm":
            return self.settings.minilm_model_name
        return "tfidf"

    def _load_or_build_vectors(self, corpus_texts: list[str]) -> np.ndarray:
        path = self.settings.vector_cache_path
        expected_dim = self.embedder.encode(["probe"]).shape[1]
        if path.exists():
            try:
                data = np.load(path, allow_pickle=False)
                cached_hash = str(data["corpus_hash"].item())
                cached_backend = str(data["backend"].item())
                cached_model = str(data["model_tag"].item())
                vectors = data["vectors"].astype(np.float32)
                if (
                    cached_hash == self._corpus_hash
                    and cached_backend == self.embedder.name
                    and cached_model == self._cache_model_tag()
                    and vectors.shape[1] == expected_dim
                ):
                    logger.info("Loaded corpus vectors from cache: %s", path)
                    return vectors
                logger.info("Ignoring stale corpus vector cache: %s", path)
            except Exception as exc:  # noqa: BLE001
                logger.warning("Failed to load vector cache (%s): %s", path, exc)

        vectors = self.embedder.encode(corpus_texts).astype(np.float32)
        try:
            np.savez_compressed(
                path,
                vectors=vectors,
                corpus_hash=np.array(self._corpus_hash),
                backend=np.array(self.embedder.name),
                model_tag=np.array(self._cache_model_tag()),
            )
            logger.info("Saved corpus vectors to cache: %s", path)
        except Exception as exc:  # noqa: BLE001
            logger.warning("Failed to save vector cache (%s): %s", path, exc)
        return vectors

    # -- semantic layer ---------------------------------------------------
    def _semantic(self, text: str) -> tuple[float, list[SemanticMatch]]:
        query_vec = self.embedder.encode([text])
        sims = cosine_similarity_matrix(query_vec, self.corpus_vectors)[0]
        k = min(self.settings.semantic_top_k, len(self.corpus))
        top_idx = np.argsort(sims)[::-1][:k]

        matches: list[SemanticMatch] = []
        for idx in top_idx:
            entry = self.corpus[int(idx)]
            snippet = entry.text if len(entry.text) <= 160 else entry.text[:157] + "..."
            matches.append(
                SemanticMatch(
                    corpus_id=entry.corpus_id,
                    category=entry.category,
                    similarity=round(float(sims[idx]), 4),
                    snippet=snippet,
                )
            )
        # The single nearest match drives the sub-score; clamp negatives to 0.
        top_sim = max(0.0, float(sims[top_idx[0]])) if len(top_idx) else 0.0
        semantic_score = round(top_sim * 100.0, 2)
        return semantic_score, matches

    # -- public API -------------------------------------------------------
    def analyze(self, text: str) -> Verdict:
        start = time.perf_counter()

        hits = heuristics.scan(text)
        h_score = heuristics.heuristic_score(hits)

        s_score, matches = self._semantic(text)
        # Only matches above the configured threshold count as corroborating signal.
        strong_matches = [
            m for m in matches if m.similarity >= self.settings.semantic_hit_threshold
        ]
        effective_semantic = s_score if strong_matches else min(s_score, 40.0)

        base_weighted = (
            self.settings.weight_heuristics * h_score
            + self.settings.weight_semantic * effective_semantic
        )
        # Defense-in-depth: if deterministic heuristics or strong semantic hits independently
        # reach high confidence, do not suppress the verdict due to lack of cross-layer signal.
        signal_floor = 0.0
        if h_score >= self.settings.block_threshold:
            signal_floor = max(signal_floor, h_score)
        if strong_matches and s_score >= self.settings.block_threshold:
            signal_floor = max(signal_floor, s_score)

        weighted = round(min(100.0, max(0.0, max(base_weighted, signal_floor))), 2)

        decision = (
            Decision.BLOCK if weighted >= self.settings.block_threshold else Decision.ALLOW
        )

        categories = self._collect_categories(hits, strong_matches)
        reason = self._explain(decision, weighted, hits, strong_matches)

        latency_ms = round((time.perf_counter() - start) * 1000.0, 2)

        return Verdict(
            decision=decision,
            risk_score=weighted,
            block_threshold=self.settings.block_threshold,
            categories=categories,
            heuristic_hits=hits,
            semantic_matches=matches,
            breakdown=RiskBreakdown(
                heuristic_score=h_score,
                semantic_score=effective_semantic,
                weighted_score=weighted,
                embedding_backend=self.embedder.name,
            ),
            reason=reason,
            latency_ms=latency_ms,
        )

    @staticmethod
    def _collect_categories(hits, strong_matches) -> list[Category]:
        cats: list[Category] = []
        for h in hits:
            if h.category not in cats:
                cats.append(h.category)
        for m in strong_matches:
            if m.category not in cats and m.category != Category.BENIGN:
                cats.append(m.category)
        return cats

    @staticmethod
    def _explain(decision, score, hits, strong_matches) -> str:
        if decision == Decision.ALLOW and not hits and not strong_matches:
            return f"No suspicious signals detected (risk {score})."
        parts: list[str] = []
        if hits:
            rule_ids = ", ".join(sorted({h.rule_id for h in hits}))
            parts.append(f"{len(hits)} heuristic rule(s) fired [{rule_ids}]")
        if strong_matches:
            top = strong_matches[0]
            parts.append(
                f"semantically similar to known attack {top.corpus_id} "
                f"(sim={top.similarity})"
            )
        verb = "Blocked" if decision == Decision.BLOCK else "Allowed"
        return f"{verb} at risk {score}: " + "; ".join(parts) + "."


@lru_cache
def get_engine() -> DetectionEngine:
    """Cached engine singleton (corpus embedded once)."""
    return DetectionEngine(get_settings())

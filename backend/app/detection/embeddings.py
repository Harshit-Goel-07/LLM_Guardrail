"""Semantic similarity backends with graceful degradation.

Two interchangeable backends implement the same ``Embedder`` protocol:

* ``MiniLMEmbedder`` — sentence-transformers ``all-MiniLM-L6-v2`` (~90 MB). Produces
  dense semantic embeddings; best accuracy, requires a one-time model download.
* ``TfidfEmbedder``  — scikit-learn TF-IDF + cosine similarity. Zero download,
  fully offline, tiny, fast. A lexical fallback that still catches paraphrases
  that share vocabulary with known attacks.

``build_embedder`` picks MiniLM when available (per settings) and silently falls
back to TF-IDF otherwise. This is the "runs anywhere" guarantee: the demo never
hard-fails just because a model couldn't be downloaded on a locked-down machine.
"""
from __future__ import annotations

import logging
from typing import Protocol, Sequence

import numpy as np

logger = logging.getLogger(__name__)


class Embedder(Protocol):
    """Common interface for both semantic backends."""

    name: str

    def encode(self, texts: Sequence[str]) -> np.ndarray:  # -> (n, dim), L2-normalized
        ...


def _l2_normalize(matrix: np.ndarray) -> np.ndarray:
    norms = np.linalg.norm(matrix, axis=1, keepdims=True)
    norms[norms == 0] = 1.0
    return matrix / norms


class MiniLMEmbedder:
    """Dense embeddings via sentence-transformers (lazy, download-once)."""

    def __init__(self, model_name: str) -> None:
        from sentence_transformers import SentenceTransformer  # heavy import, deferred

        self.name = "minilm"
        self._model = SentenceTransformer(model_name)

    def encode(self, texts: Sequence[str]) -> np.ndarray:
        vectors = self._model.encode(
            list(texts),
            convert_to_numpy=True,
            normalize_embeddings=True,
            show_progress_bar=False,
        )
        return vectors.astype(np.float32)


class TfidfEmbedder:
    """Lexical fallback: TF-IDF vectors, cosine-comparable after L2 normalization."""

    def __init__(self, corpus_texts: Sequence[str]) -> None:
        from sklearn.feature_extraction.text import TfidfVectorizer

        self.name = "tfidf"
        self._vectorizer = TfidfVectorizer(
            lowercase=True,
            ngram_range=(1, 3),
            min_df=1,
            sublinear_tf=True,
            strip_accents="unicode",
            token_pattern=r"(?u)\b\w+\b",
        )
        # Fit on the corpus so the vocabulary reflects known-attack language.
        self._vectorizer.fit(list(corpus_texts))

    def encode(self, texts: Sequence[str]) -> np.ndarray:
        matrix = self._vectorizer.transform(list(texts)).toarray().astype(np.float32)
        return _l2_normalize(matrix)


def build_embedder(
    backend: str,
    minilm_model_name: str,
    corpus_texts: Sequence[str],
) -> Embedder:
    """Construct the best available embedder given the configured preference.

    backend: "auto" | "minilm" | "tfidf"
    """
    want_minilm = backend in ("auto", "minilm")
    if want_minilm:
        try:
            embedder = MiniLMEmbedder(minilm_model_name)
            logger.info("Semantic backend: MiniLM (%s)", minilm_model_name)
            return embedder
        except Exception as exc:  # noqa: BLE001 - any failure ⇒ fall back
            if backend == "minilm":
                raise
            logger.warning(
                "MiniLM unavailable (%s); falling back to TF-IDF. "
                "Install sentence-transformers or allow the model download for "
                "full semantic accuracy.",
                exc,
            )
    logger.info("Semantic backend: TF-IDF (offline fallback)")
    return TfidfEmbedder(corpus_texts)


def cosine_similarity_matrix(query: np.ndarray, corpus: np.ndarray) -> np.ndarray:
    """Cosine similarity between L2-normalized query rows and corpus rows.

    Returns an (n_query, n_corpus) matrix. Both inputs are assumed normalized, so
    the dot product equals cosine similarity.
    """
    return query @ corpus.T

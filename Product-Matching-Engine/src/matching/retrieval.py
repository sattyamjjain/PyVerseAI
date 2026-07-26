"""Hybrid retrieval: sparse + dense rankers fused with Reciprocal Rank Fusion.

Sparse and dense retrievers fail in opposite directions — BM25/TF-IDF nail
rare exact tokens (article numbers, dimensions, series names) while embeddings
connect paraphrases ("Wand-Tiefspuelklosett" ~ "Wand-WC Tiefspueler"). RRF
fuses their rank lists without having to calibrate incompatible scores.
"""
import logging
from typing import Optional, Sequence

import numpy as np
import pandas as pd

from .dense import Embedder, has_openai_key
from .sparse import SparseIndex
from .text_utils import normalize, product_doc, requirement_text

logger = logging.getLogger(__name__)

RRF_K = 60


def _rrf_from_rankings(rankings: Sequence[np.ndarray], n_docs: int, depth: int = 100) -> np.ndarray:
    """Fuse per-ranker score matrices into RRF scores, shape (n_queries, n_docs)."""
    depth = min(depth, n_docs)
    n_queries = rankings[0].shape[0]
    fused = np.zeros((n_queries, n_docs), dtype=np.float32)
    for scores in rankings:
        top = np.argsort(-scores, axis=1)[:, :depth]
        for qi in range(n_queries):
            fused[qi, top[qi]] += 1.0 / (RRF_K + np.arange(1, depth + 1))
    return fused


class HybridRetriever:
    """Ranks catalog products (and optionally historical precedents) for queries."""

    def __init__(self, products: pd.DataFrame, use_dense: bool = True) -> None:
        self.products = products.reset_index(drop=True)
        self.product_ids: list[str] = self.products["product_id"].tolist()
        docs = product_doc(self.products).tolist()
        self._sparse = SparseIndex(docs)
        self._embedder: Optional[Embedder] = None
        self._doc_vecs: Optional[np.ndarray] = None
        if use_dense and has_openai_key():
            self._embedder = Embedder()
            self._doc_vecs = self._embedder.embed(docs)
        elif use_dense:
            logger.warning("OPENAI_API_KEY not set — dense retrieval disabled, using sparse only.")

    def sparse_scores(self, queries: Sequence[str]) -> np.ndarray:
        """TF-IDF-only relevance (no API) — used by the deterministic fallback."""
        return self._sparse.tfidf_scores(queries)

    def score_matrix(self, queries: Sequence[str]) -> np.ndarray:
        """RRF-fused relevance of every product for every query."""
        rankers = [self._sparse.tfidf_scores(queries), self._sparse.bm25_scores(queries)]
        if self._embedder is not None and self._doc_vecs is not None:
            q_vecs = self._embedder.embed(list(queries))
            rankers.append(q_vecs @ self._doc_vecs.T)
        return _rrf_from_rankings(rankers, len(self.product_ids))

    def top_k(self, queries: Sequence[str], k: int = 20) -> list[list[tuple[str, float]]]:
        """Top-k (product_id, rrf_score) per query."""
        fused = self.score_matrix(queries)
        order = np.argsort(-fused, axis=1)[:, :k]
        return [
            [(self.product_ids[j], float(fused[qi, j])) for j in order[qi]]
            for qi in range(len(queries))
        ]


class PrecedentIndex:
    """Nearest historical requirements (labeled) — used as few-shot evidence."""

    def __init__(self, requirements: pd.DataFrame, use_dense: bool = True) -> None:
        self.requirements = requirements.reset_index(drop=True)
        self._texts = requirement_text(self.requirements).tolist()
        self._labels: list[str] = self.requirements["product_id"].tolist()
        self._sparse = SparseIndex(self._texts)
        self._embedder: Optional[Embedder] = None
        self._vecs: Optional[np.ndarray] = None
        if use_dense and has_openai_key():
            self._embedder = Embedder()
            self._vecs = self._embedder.embed(self._texts)

    def top_k(
        self, queries: Sequence[str], k: int = 3, exclude_identical: bool = False
    ) -> list[list[tuple[str, str, float]]]:
        """Top-k (historical_text, chosen_product_id, score) per query.

        exclude_identical drops precedents whose normalized text equals the
        query's — leave-one-out discipline so that evaluating on labeled data
        never hands the model its own row as "evidence".
        """
        if not queries:
            return []
        rankers = [self._sparse.tfidf_scores(queries)]
        if self._embedder is not None and self._vecs is not None:
            rankers.append((self._embedder.embed(list(queries)) @ self._vecs.T + 1.0) / 2.0)
        blended = np.mean(rankers, axis=0)
        depth = min(k + 20 if exclude_identical else k, blended.shape[1])
        order = np.argsort(-blended, axis=1)[:, :depth]
        results: list[list[tuple[str, str, float]]] = []
        for qi, query in enumerate(queries):
            query_norm = normalize(query)
            per_query: list[tuple[str, str, float]] = []
            for j in order[qi]:
                if exclude_identical and normalize(self._texts[j]) == query_norm:
                    continue
                per_query.append((self._texts[j], self._labels[j], float(blended[qi, j])))
                if len(per_query) == k:
                    break
            results.append(per_query)
        return results

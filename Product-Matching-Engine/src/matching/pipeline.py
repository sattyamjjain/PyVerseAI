"""End-to-end matching pipelines (the 3 delivered methods).

Method 1  deterministic : article-number extraction, TF-IDF fallback
Method 2  hybrid        : sparse+dense RRF retrieval, top-1
Method 3  llm           : extraction short-circuit -> hybrid top-k + precedents -> LLM selection
"""
import logging
from typing import Optional, Sequence

import numpy as np
import pandas as pd
from pydantic import BaseModel

from .dense import has_openai_key
from .extraction import extract_all
from .retrieval import HybridRetriever, PrecedentIndex
from .text_utils import requirement_text

logger = logging.getLogger(__name__)


class MatcherConfig(BaseModel):
    # k=40 chosen via experiments/04_llm_rerank_ablation.py (0.685 vs 0.625 at k=20):
    # retrieval recall keeps climbing past top-20 and the LLM handles the longer list well
    candidates_k: int = 40
    precedents_k: int = 3
    use_dense: bool = True
    use_precedents: bool = True
    llm_model: Optional[str] = None


class Matcher:
    """Holds the fitted indexes; exposes the three prediction methods."""

    def __init__(
        self,
        products: pd.DataFrame,
        precedents: Optional[pd.DataFrame] = None,
        config: Optional[MatcherConfig] = None,
    ) -> None:
        self.config = config or MatcherConfig()
        self.products = products.reset_index(drop=True)
        self._by_id = self.products.set_index("product_id")
        self._catalog_ids = frozenset(self.products["product_id"])
        self.retriever = HybridRetriever(self.products, use_dense=self.config.use_dense)
        self.precedent_index: Optional[PrecedentIndex] = None
        if self.config.use_precedents and precedents is not None and len(precedents):
            self.precedent_index = PrecedentIndex(precedents, use_dense=self.config.use_dense)
        self._reranker = None

    # ---------- Method 1: deterministic cascade ----------
    def predict_deterministic(self, df: pd.DataFrame) -> list[str]:
        """Extracted article number when present (first match), else TF-IDF top-1."""
        queries = requirement_text(df).tolist()
        extracted = extract_all(queries, self._catalog_ids)
        scores = self.retriever._sparse.tfidf_scores(queries)
        fallback = [self.retriever.product_ids[j] for j in np.argmax(scores, axis=1)]
        return [ids[0] if ids else fb for ids, fb in zip(extracted, fallback)]

    # ---------- Method 2: hybrid retrieval ----------
    def predict_hybrid(self, df: pd.DataFrame) -> list[str]:
        queries = requirement_text(df).tolist()
        return [ranked[0][0] for ranked in self.retriever.top_k(queries, k=1)]

    # ---------- Method 3: full pipeline with LLM rerank ----------
    def predict_llm(self, df: pd.DataFrame) -> list[str]:
        if not has_openai_key():
            logger.warning("No OPENAI_API_KEY — falling back to hybrid retrieval.")
            return self.predict_hybrid(df)
        queries = requirement_text(df).tolist()
        extracted = extract_all(queries, self._catalog_ids)
        candidates_list = self._build_candidates(queries, extracted)
        precedents_list = self._build_precedents(queries)
        single_id = [len(ids) == 1 for ids in extracted]
        todo = [i for i, solo in enumerate(single_id) if not solo]
        choices = self._get_reranker().choose_batch(
            [queries[i] for i in todo],
            [candidates_list[i] for i in todo],
            [precedents_list[i] for i in todo],
        )
        preds: list[str] = [ids[0] if solo else "" for ids, solo in zip(extracted, single_id)]
        for i, choice in zip(todo, choices):
            preds[i] = choice.product_id
        return preds

    def _get_reranker(self):
        if self._reranker is None:
            from .rerank import LLMReranker

            self._reranker = LLMReranker(model=self.config.llm_model)
            logger.info("Rerank model: %s", self._reranker.model)
        return self._reranker

    def _build_candidates(self, queries: Sequence[str], extracted: Sequence[list[str]]) -> list[list[dict]]:
        """Hybrid top-k per query; extracted ids are force-included at the top."""
        retrieved = self.retriever.top_k(queries, k=self.config.candidates_k)
        out: list[list[dict]] = []
        for ids, ranked in zip(extracted, retrieved):
            ordered = list(dict.fromkeys(ids + [pid for pid, _ in ranked]))[: self.config.candidates_k]
            out.append([self._product_dict(pid) for pid in ordered])
        return out

    def _build_precedents(self, queries: Sequence[str]) -> list[list[tuple[str, str, str]]]:
        if self.precedent_index is None:
            return [[] for _ in queries]
        result = self.precedent_index.top_k(queries, k=self.config.precedents_k)
        return [
            [(text, pid, self._product_name(pid)) for text, pid, _ in per_query]
            for per_query in result
        ]

    def _product_dict(self, product_id: str) -> dict:
        row = self._by_id.loc[product_id]
        return {
            "product_id": product_id,
            "name": row["name"],
            "description": row["description"],
            "category": row["category"],
        }

    def _product_name(self, product_id: str) -> str:
        return str(self._by_id.loc[product_id, "name"]) if product_id in self._by_id.index else ""

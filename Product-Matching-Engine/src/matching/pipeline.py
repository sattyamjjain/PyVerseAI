"""End-to-end matching pipelines (the 3 delivered methods).

Method 1  deterministic : article-number extraction, TF-IDF fallback
Method 2  hybrid        : sparse+dense RRF retrieval, top-1
Method 3  llm           : extraction short-circuit -> hybrid top-k + precedents -> LLM selection

Precedent leave-one-out: by default, precedents whose text is identical to the
query are excluded from the LLM prompt (exclude_identical_precedents=True).
When evaluating on the labeled dataset this prevents the model from being
handed its own row's answer as "evidence" — a leak we measured at +0.216 on
the full-set metric (a copy-the-precedent baseline alone scores 0.894).
A production system could re-enable exact-history reuse as an explicit
deterministic stage instead of hiding it inside the LLM prompt.
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
    # k=40: the 200-row leave-one-out sweep (experiments/04) is flat across k
    # (0.535-0.540, CI ~±0.07), but the full-run comparison at n=1000 gives
    # k=40 0.524 vs k=20 0.507, and retrieval recall@40 (0.769) is well above
    # recall@20 (0.684). Decision history in SOLUTION.md.
    candidates_k: int = 40
    precedents_k: int = 3
    use_dense: bool = True
    use_precedents: bool = True
    exclude_identical_precedents: bool = True
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
        self._id_to_idx = {pid: i for i, pid in enumerate(self.products["product_id"])}
        self.retriever = HybridRetriever(self.products, use_dense=self.config.use_dense)
        self.precedent_index: Optional[PrecedentIndex] = None
        self._most_common_label: str = self.products["product_id"].iloc[0]
        if precedents is not None and len(precedents):
            self._most_common_label = str(precedents["product_id"].value_counts().idxmax())
            if self.config.use_precedents:
                self.precedent_index = PrecedentIndex(precedents, use_dense=self.config.use_dense)
        self._reranker = None
        self.last_run_stats: dict = {}

    # ---------- Method 1: deterministic cascade ----------
    def predict_deterministic(self, df: pd.DataFrame) -> list[str]:
        """Extracted article number when present, else TF-IDF top-1.

        When several catalog ids are cited, the one whose product best matches
        the text (by TF-IDF) wins. Rows with zero lexical signal fall back to
        the most common historical product instead of an arbitrary catalog row.
        """
        queries = requirement_text(df).tolist()
        if not queries:
            return []
        extracted = extract_all(queries, self._catalog_ids)
        scores = self.retriever.sparse_scores(queries)
        preds: list[str] = []
        for qi, ids in enumerate(extracted):
            if len(ids) == 1:
                preds.append(ids[0])
            elif len(ids) > 1:
                preds.append(max(ids, key=lambda pid: scores[qi, self._id_to_idx[pid]]))
            elif scores[qi].max() <= 0.0:
                preds.append(self._most_common_label)
            else:
                preds.append(self.retriever.product_ids[int(np.argmax(scores[qi]))])
        return preds

    # ---------- Method 2: hybrid retrieval ----------
    def predict_hybrid(self, df: pd.DataFrame) -> list[str]:
        queries = requirement_text(df).tolist()
        if not queries:
            return []
        return [ranked[0][0] for ranked in self.retriever.top_k(queries, k=1)]

    # ---------- Method 3: full pipeline with LLM rerank ----------
    def predict_llm(self, df: pd.DataFrame) -> list[str]:
        if not has_openai_key():
            logger.warning("No OPENAI_API_KEY — falling back to the deterministic cascade.")
            return self.predict_deterministic(df)
        queries = requirement_text(df).tolist()
        if not queries:
            return []
        extracted = extract_all(queries, self._catalog_ids)
        preds: list[str] = [ids[0] if len(ids) == 1 else "" for ids in extracted]
        todo = [i for i, ids in enumerate(extracted) if len(ids) != 1]
        if todo:
            todo_queries = [queries[i] for i in todo]
            candidates_list = self._build_candidates(todo_queries, [extracted[i] for i in todo])
            precedents_list = self._build_precedents(todo_queries)
            choices = self._get_reranker().choose_batch(todo_queries, candidates_list, precedents_list)
            n_fallback = 0
            for i, choice in zip(todo, choices):
                preds[i] = choice.product_id
                n_fallback += choice.reasoning == "fallback"
            self.last_run_stats = {
                "n_rows": len(queries),
                "n_short_circuit": len(queries) - len(todo),
                "n_llm": len(todo),
                "n_llm_fallback": n_fallback,
            }
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
        result = self.precedent_index.top_k(
            queries,
            k=self.config.precedents_k,
            exclude_identical=self.config.exclude_identical_precedents,
        )
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

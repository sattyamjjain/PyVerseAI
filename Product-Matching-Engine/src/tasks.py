"""Deliverable: predict_product_id (best method) plus one function per method.

All functions share the required signature: they take a DataFrame with
'requirement' and 'requirement_detail' columns and return a list of
product_ids in the same row order.

Method 3 (LLM pipeline) is the default. It degrades gracefully: without an
OPENAI_API_KEY it automatically falls back to the deterministic cascade
(the strongest offline method), so this file always runs.
"""
from typing import Iterable, Optional

import pandas as pd

from src.load_data import load_products, load_requirements
from src.matching.pipeline import Matcher, MatcherConfig

_matcher: Optional[Matcher] = None
_matcher_offline: Optional[Matcher] = None


def _get_matcher() -> Matcher:
    """Lazily build the shared matcher (catalog + historical precedent indexes)."""
    global _matcher
    if _matcher is None:
        _matcher = Matcher(products=load_products(), precedents=load_requirements())
    return _matcher


def _get_offline_matcher() -> Matcher:
    """Dense-free matcher: no embedding calls, for the API-free methods."""
    global _matcher_offline
    if _matcher_offline is None:
        _matcher_offline = Matcher(
            products=load_products(),
            precedents=load_requirements(),
            config=MatcherConfig(use_dense=False, use_precedents=False),
        )
    return _matcher_offline


def predict_product_id(df: pd.DataFrame) -> Iterable[str]:
    """Best method (Method 3): extraction -> hybrid retrieval -> LLM selection."""
    return _get_matcher().predict_llm(df)


def predict_product_id_deterministic(df: pd.DataFrame) -> Iterable[str]:
    """Method 1: article-number extraction with TF-IDF fallback (no API calls)."""
    return _get_offline_matcher().predict_deterministic(df)


def predict_product_id_hybrid(df: pd.DataFrame) -> Iterable[str]:
    """Method 2: hybrid retrieval with RRF fusion, top-1 (embeddings only if key set)."""
    return _get_matcher().predict_hybrid(df)

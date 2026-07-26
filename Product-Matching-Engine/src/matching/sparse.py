"""Sparse (lexical) retrieval: word/char TF-IDF and BM25.

Char n-grams are essential for German compounds ("Tiefspuelklosett" vs
"Tiefspuel-WC") and for partial article numbers / dimension strings.
"""
from typing import Sequence

import numpy as np
from rank_bm25 import BM25Okapi
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.preprocessing import normalize as l2_normalize

from .text_utils import normalize


class SparseIndex:
    """TF-IDF (word + char_wb) cosine and BM25 rankings over a fixed corpus."""

    def __init__(self, docs: Sequence[str]) -> None:
        self._word = TfidfVectorizer(preprocessor=normalize, ngram_range=(1, 2), sublinear_tf=True)
        self._char = TfidfVectorizer(
            preprocessor=normalize, analyzer="char_wb", ngram_range=(3, 5), sublinear_tf=True
        )
        self._word_mat = l2_normalize(self._word.fit_transform(docs))
        self._char_mat = l2_normalize(self._char.fit_transform(docs))
        self._bm25 = BM25Okapi([normalize(d).split() for d in docs])

    def tfidf_scores(self, queries: Sequence[str]) -> np.ndarray:
        """Blended word+char TF-IDF cosine similarity, shape (n_queries, n_docs)."""
        qw = l2_normalize(self._word.transform(queries))
        qc = l2_normalize(self._char.transform(queries))
        return 0.4 * (qw @ self._word_mat.T).toarray() + 0.6 * (qc @ self._char_mat.T).toarray()

    def bm25_scores(self, queries: Sequence[str]) -> np.ndarray:
        return np.array([self._bm25.get_scores(normalize(q).split()) for q in queries])

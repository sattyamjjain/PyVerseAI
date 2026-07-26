"""Experiment 03 — which retriever earns its place? (sparse vs dense vs hybrid)

Measures top-1 accuracy and top-k recall of every individual ranker and the
RRF fusion. Recall@k is the ceiling for any downstream reranker: if the target
is not in the candidate list, no LLM can pick it.

Run: .venv/bin/python experiments/03_retrieval_ablation.py [--no-dense]
"""
import argparse
import json
import os
import sys

import numpy as np

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.load_data import load_products, load_requirements  # noqa: E402
from src.matching.dense import Embedder, has_openai_key  # noqa: E402
from src.matching.retrieval import _rrf_from_rankings  # noqa: E402
from src.matching.sparse import SparseIndex  # noqa: E402
from src.matching.text_utils import product_doc, requirement_text  # noqa: E402

KS = (1, 5, 10, 20, 50)


def recall_at(scores: np.ndarray, product_ids: list[str], targets: list[str]) -> dict[str, float]:
    order = np.argsort(-scores, axis=1)[:, : max(KS)]
    ranked_ids = [[product_ids[j] for j in row] for row in order]
    return {f"recall@{k}": float(np.mean([t in r[:k] for t, r in zip(targets, ranked_ids)])) for k in KS}


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--no-dense", action="store_true")
    args = parser.parse_args()

    products = load_products()
    requirements = load_requirements()
    docs = product_doc(products).tolist()
    product_ids = products["product_id"].tolist()
    queries = requirement_text(requirements).tolist()
    targets = requirements["product_id"].tolist()

    sparse = SparseIndex(docs)
    rankers: dict[str, np.ndarray] = {
        "tfidf_word_char": sparse.tfidf_scores(queries),
        "bm25": sparse.bm25_scores(queries),
    }
    if not args.no_dense and has_openai_key():
        embedder = Embedder()
        rankers["dense_openai"] = embedder.embed(queries) @ embedder.embed(docs).T
    else:
        print("NOTE: dense ranker skipped (no key or --no-dense)")

    results = {name: recall_at(scores, product_ids, targets) for name, scores in rankers.items()}
    fused = _rrf_from_rankings(list(rankers.values()), len(product_ids))
    results["hybrid_rrf"] = recall_at(fused, product_ids, targets)

    for name, metrics in results.items():
        print(f"\n{name}")
        for k, v in metrics.items():
            print(f"  {k:10s} {v:.3f}")

    out = os.path.join(os.path.dirname(os.path.abspath(__file__)), "results", "retrieval_ablation.json")
    os.makedirs(os.path.dirname(out), exist_ok=True)
    with open(out, "w") as fh:
        json.dump(results, fh, indent=2)
    print(f"\nSaved -> {out}")


if __name__ == "__main__":
    main()

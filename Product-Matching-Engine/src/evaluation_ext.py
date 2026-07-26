"""Evaluation extensions beyond the provided accuracy metric.

Adds what the plain full-dataset accuracy hides:
- duplicate-aware unseen split (171/1000 rows are exact duplicate pairs; methods
  that consult historical precedents would otherwise score on memorization)
- top-k retrieval recall (the ceiling for any reranker)
- per-category and per-stage breakdowns
"""
import hashlib
from typing import Callable, Iterable, Optional

import numpy as np
import pandas as pd

from src.evaluate import accuracy
from src.matching.extraction import extract_all
from src.matching.pipeline import Matcher, MatcherConfig
from src.matching.text_utils import normalize, requirement_text


def _group_hash(texts: pd.Series) -> pd.Series:
    """Stable group key per normalized requirement text (duplicates share a group)."""
    return texts.map(lambda t: hashlib.md5(normalize(t).encode()).hexdigest())


def unseen_split(requirements: pd.DataFrame, test_frac: float = 0.2, seed: int = 42) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Split so that duplicate/near-identical texts never straddle train and test."""
    groups = _group_hash(requirement_text(requirements))
    unique_groups = groups.drop_duplicates().tolist()
    rng = np.random.default_rng(seed)
    test_groups = set(rng.choice(unique_groups, size=int(len(unique_groups) * test_frac), replace=False))
    mask = groups.isin(test_groups)
    return requirements[~mask].reset_index(drop=True), requirements[mask].reset_index(drop=True)


def eval_full_dataset(
    requirements: pd.DataFrame, methods: dict[str, Callable[[pd.DataFrame], Iterable[str]]]
) -> dict[str, float]:
    """The challenge's own metric: accuracy over the full labeled set."""
    inputs = requirements[["requirement", "requirement_detail"]]
    return {name: accuracy(fn(inputs), requirements["product_id"]) for name, fn in methods.items()}


def eval_unseen(
    products: pd.DataFrame,
    requirements: pd.DataFrame,
    config: Optional[MatcherConfig] = None,
    seed: int = 42,
) -> dict[str, float]:
    """Honest generalization: precedent index sees only train rows, eval on held-out."""
    train, test = unseen_split(requirements, seed=seed)
    matcher = Matcher(products=products, precedents=train, config=config)
    inputs = test[["requirement", "requirement_detail"]]
    targets = test["product_id"]
    results = {
        "deterministic": accuracy(matcher.predict_deterministic(inputs), targets),
        "hybrid": accuracy(matcher.predict_hybrid(inputs), targets),
    }
    from src.matching.dense import has_openai_key

    if has_openai_key():
        results["llm"] = accuracy(matcher.predict_llm(inputs), targets)
    return results


def topk_recall(matcher: Matcher, requirements: pd.DataFrame, ks: tuple[int, ...] = (1, 5, 10, 20, 50)) -> dict[int, float]:
    """Is the target anywhere in the retriever's top-k? Upper bound for reranking."""
    queries = requirement_text(requirements).tolist()
    targets = requirements["product_id"].tolist()
    ranked = matcher.retriever.top_k(queries, k=max(ks))
    return {
        k: float(np.mean([t in [pid for pid, _ in r[:k]] for t, r in zip(targets, ranked)]))
        for k in ks
    }


def extraction_stage_stats(matcher: Matcher, requirements: pd.DataFrame) -> dict[str, float]:
    """Coverage and precision of the deterministic article-number stage."""
    queries = requirement_text(requirements).tolist()
    targets = requirements["product_id"].tolist()
    extracted = extract_all(queries, matcher._catalog_ids)
    covered = [(ids, t) for ids, t in zip(extracted, targets) if ids]
    return {
        "coverage": len(covered) / len(targets),
        "precision_first": float(np.mean([ids[0] == t for ids, t in covered])) if covered else 0.0,
        "target_in_extracted": float(np.mean([t in ids for ids, t in covered])) if covered else 0.0,
    }


def per_category_accuracy(
    products: pd.DataFrame, requirements: pd.DataFrame, preds: Iterable[str]
) -> pd.DataFrame:
    df = requirements.assign(pred=list(preds))
    df = df.merge(products[["product_id", "category"]], on="product_id", how="left")
    df["correct"] = df["pred"] == df["product_id"]
    return (
        df.groupby("category")["correct"].agg(["mean", "count"]).sort_values("count", ascending=False)
    )

"""Evaluate all matching methods and write results tables.

Usage:
    python scripts/run_eval.py            # everything the key allows
    python scripts/run_eval.py --no-llm   # sparse/local methods only
    python scripts/run_eval.py --limit 100
"""
import argparse
import json
import logging
import os
import sys
import time

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.evaluation_ext import (  # noqa: E402
    eval_unseen,
    extraction_stage_stats,
    per_category_accuracy,
    topk_recall,
)
from src.load_data import load_products, load_requirements  # noqa: E402
from src.matching.dense import has_openai_key  # noqa: E402
from src.matching.pipeline import Matcher, MatcherConfig  # noqa: E402

logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--no-llm", action="store_true", help="skip the LLM method")
    parser.add_argument("--no-dense", action="store_true", help="skip OpenAI embeddings")
    parser.add_argument("--limit", type=int, default=None, help="evaluate on first N rows")
    args = parser.parse_args()

    products = load_products()
    requirements = load_requirements()
    if args.limit:
        requirements = requirements.head(args.limit)
    inputs = requirements[["requirement", "requirement_detail"]]
    targets = requirements["product_id"]

    config = MatcherConfig(use_dense=not args.no_dense)
    matcher = Matcher(products=products, precedents=load_requirements(), config=config)

    results: dict = {"stages": {}, "full_dataset": {}, "unseen_split": {}, "timing_s": {}}
    results["stages"]["extraction"] = extraction_stage_stats(matcher, requirements)
    results["stages"]["retrieval_topk_recall"] = topk_recall(matcher, requirements)

    from src.evaluate import accuracy

    methods = {
        "method1_deterministic": matcher.predict_deterministic,
        "method2_hybrid": matcher.predict_hybrid,
    }
    if not args.no_llm and has_openai_key():
        methods["method3_llm"] = matcher.predict_llm
    elif not args.no_llm:
        print("NOTE: OPENAI_API_KEY not found — skipping method3_llm.")

    best_preds = None
    for name, fn in methods.items():
        start = time.time()
        preds = list(fn(inputs))
        results["timing_s"][name] = round(time.time() - start, 1)
        results["full_dataset"][name] = accuracy(preds, targets)
        best_preds = preds

    results["unseen_split"] = eval_unseen(products, requirements, config=config)

    print("\n=== Extraction stage ===")
    print(json.dumps(results["stages"]["extraction"], indent=2))
    print("\n=== Retrieval top-k recall (ceiling for reranking) ===")
    print(json.dumps(results["stages"]["retrieval_topk_recall"], indent=2))
    print("\n=== Accuracy, full labeled set (challenge metric) ===")
    for name, acc in results["full_dataset"].items():
        print(f"  {name:26s} {acc:.3f}   ({results['timing_s'][name]}s)")
    print("\n=== Accuracy, duplicate-aware unseen split ===")
    for name, acc in results["unseen_split"].items():
        print(f"  {name:26s} {acc:.3f}")
    if best_preds is not None:
        print("\n=== Per-category accuracy (best method) ===")
        print(per_category_accuracy(products, requirements, best_preds))

    out_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "experiments", "results", "results.json")
    os.makedirs(os.path.dirname(out_path), exist_ok=True)
    with open(out_path, "w") as fh:
        json.dump(results, fh, indent=2)
    print(f"\nSaved -> {out_path}")


if __name__ == "__main__":
    main()

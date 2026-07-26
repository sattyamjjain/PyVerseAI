"""Evaluate all matching methods and write results tables.

Usage:
    python scripts/run_eval.py            # everything the key allows
    python scripts/run_eval.py --no-llm --no-dense   # fully offline, zero API calls
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
    precedent_copy_baseline,
    topk_recall,
)
from src.load_data import load_products, load_requirements  # noqa: E402
from src.matching.dense import EMBED_MODEL, has_openai_key  # noqa: E402
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
    matcher = Matcher(products=products, precedents=requirements, config=config)

    results: dict = {
        "config": {
            "candidates_k": config.candidates_k,
            "precedents_k": config.precedents_k,
            "exclude_identical_precedents": config.exclude_identical_precedents,
            "embed_model": None if args.no_dense else EMBED_MODEL,
        },
        "stages": {},
        "full_dataset_loo": {},
        "unseen_split": {},
        "timing_s": {},
    }
    results["stages"]["extraction"] = extraction_stage_stats(matcher, requirements)
    results["stages"]["retrieval_topk_recall"] = topk_recall(matcher, requirements)
    results["stages"]["precedent_memorization_baseline"] = precedent_copy_baseline(matcher, requirements)

    from src.evaluate import accuracy

    methods = {
        "method1_deterministic": matcher.predict_deterministic,
        "method2_hybrid": matcher.predict_hybrid,
    }
    if not args.no_llm and has_openai_key():
        methods["method3_llm"] = matcher.predict_llm
    elif not args.no_llm:
        print("NOTE: OPENAI_API_KEY not found — skipping method3_llm.")

    all_preds: dict[str, list[str]] = {}
    for name, fn in methods.items():
        start = time.time()
        preds = list(fn(inputs))
        results["timing_s"][name] = round(time.time() - start, 1)
        results["full_dataset_loo"][name] = accuracy(preds, targets)
        all_preds[name] = preds
    if matcher.last_run_stats:
        results["config"]["rerank_model"] = matcher._get_reranker().model
        results["stages"]["llm_pipeline"] = matcher.last_run_stats

    results["unseen_split"] = eval_unseen(
        products, requirements, config=config, use_llm=not args.no_llm
    )

    print("\n=== Extraction stage ===")
    print(json.dumps(results["stages"]["extraction"], indent=2))
    print("\n=== Precedent memorization baseline (why full-set numbers need LOO) ===")
    print(json.dumps(results["stages"]["precedent_memorization_baseline"], indent=2))
    print("\n=== Retrieval top-k recall (ceiling for reranking) ===")
    print(json.dumps(results["stages"]["retrieval_topk_recall"], indent=2))
    print("\n=== Accuracy, full labeled set with leave-one-out precedents ===")
    for name, acc in results["full_dataset_loo"].items():
        print(f"  {name:26s} {acc:.3f}   ({results['timing_s'][name]}s)")
    print("\n=== Accuracy, duplicate-aware unseen split ===")
    for name, acc in results["unseen_split"].items():
        print(f"  {name:26s} {acc:.3f}")

    best_name = max(results["full_dataset_loo"], key=results["full_dataset_loo"].get)
    per_cat = per_category_accuracy(products, requirements, all_preds[best_name])
    results["per_category"] = {"method": best_name, "table": per_cat.reset_index().to_dict("records")}
    print(f"\n=== Per-category accuracy ({best_name}) ===")
    print(per_cat)

    out_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "experiments", "results")
    os.makedirs(out_dir, exist_ok=True)
    # partial runs must not clobber the canonical full-run artifact
    suffix = "_partial" if (args.no_llm or args.no_dense or args.limit) else ""
    with open(os.path.join(out_dir, f"results{suffix}.json"), "w") as fh:
        json.dump(results, fh, indent=2)
    preds_df = requirements[["requirement", "requirement_detail", "product_id"]].copy()
    for name, preds in all_preds.items():
        preds_df[name] = preds
        preds_df[f"{name}_correct"] = preds_df[name] == preds_df["product_id"]
    preds_df.to_csv(os.path.join(out_dir, f"predictions{suffix}.csv"), index=False)
    print(f"\nSaved -> {out_dir}/results{suffix}.json and predictions{suffix}.csv")


if __name__ == "__main__":
    main()

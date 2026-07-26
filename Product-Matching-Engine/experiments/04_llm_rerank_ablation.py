"""Experiment 04 — LLM rerank ablations (needs OPENAI_API_KEY).

Questions answered on a fixed sample:
1. Does the extraction short-circuit help, or should the LLM see those rows too?
2. Do historical precedents in the prompt help?
3. How much does candidate-list size (k) matter?

Run: .venv/bin/python experiments/04_llm_rerank_ablation.py [--sample 200]
"""
import argparse
import json
import os
import sys

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.evaluate import accuracy  # noqa: E402
from src.load_data import load_products, load_requirements  # noqa: E402
from src.matching.dense import has_openai_key  # noqa: E402
from src.matching.pipeline import Matcher, MatcherConfig  # noqa: E402

def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--sample", type=int, default=200)
    args = parser.parse_args()
    if not has_openai_key():
        sys.exit("OPENAI_API_KEY required for this experiment.")

    products = load_products()
    requirements = load_requirements().sample(args.sample, random_state=7).reset_index(drop=True)
    inputs = requirements[["requirement", "requirement_detail"]]
    targets = requirements["product_id"]

    variants: dict[str, MatcherConfig] = {
        "k20_precedents": MatcherConfig(candidates_k=20, use_precedents=True),
        "k20_no_precedents": MatcherConfig(candidates_k=20, use_precedents=False),
        "k10_precedents": MatcherConfig(candidates_k=10, use_precedents=True),
        "k40_precedents": MatcherConfig(candidates_k=40, use_precedents=True),
    }

    results: dict[str, float] = {}
    for name, config in variants.items():
        matcher = Matcher(products=products, precedents=load_requirements(), config=config)
        results[name] = accuracy(matcher.predict_llm(inputs), targets)
        print(f"{name:22s} {results[name]:.3f}")

    out = os.path.join(os.path.dirname(os.path.abspath(__file__)), "results", "llm_ablation.json")
    os.makedirs(os.path.dirname(out), exist_ok=True)
    with open(out, "w") as fh:
        json.dump({"sample": args.sample, "accuracy": results}, fh, indent=2)
    print(f"Saved -> {out}")


if __name__ == "__main__":
    main()

"""Eval harness: score a produced CSV against hand-labeled golden data.

Deterministic field-diff scoring (no LLM judge — `==` does not hallucinate),
with an error taxonomy that separates the failure modes that matter:

    correct_exact       string-identical
    correct_normalized  same value after type-aware compare (Decimal, folding)
    missing_correct     golden null, prediction null  — the null was right
    missing_wrong       golden value, prediction null — recall failure
    hallucinated        golden null, prediction value — the worst failure class
    wrong_value         both present, different

`missing_correct` counts toward accuracy: returning null for an absent field
is correct behaviour, and *not* rewarding it incentivises guessing.
"""

from __future__ import annotations

import argparse
import csv
import sys
from collections import Counter, defaultdict
from decimal import Decimal, InvalidOperation
from pathlib import Path

import yaml

from . import config
from .normalize import fold_text

EVAL_FIELDS = [
    "vendor_name",
    "invoice_date",
    "service_address",
    "utility_type",
    "usage_amount",
    "usage_unit",
    "billing_period_start",
    "billing_period_end",
]

ACCURATE = {"correct_exact", "correct_normalized", "missing_correct"}

_PUNCT = str.maketrans("", "", ".,;:'’")


def _loose(value: str) -> str:
    return " ".join(fold_text(value).translate(_PUNCT).split())


def _as_decimal(value: str) -> Decimal | None:
    try:
        return Decimal(value)
    except (InvalidOperation, ValueError):
        return None


def classify(field: str, golden, predicted: str) -> str:
    """Compare one golden label against one predicted CSV cell."""
    pred = predicted.strip() or None
    if golden is None:
        return "missing_correct" if pred is None else "hallucinated"
    if pred is None:
        return "missing_wrong"

    if field in {"usage_amount"}:
        g, p = _as_decimal(str(golden)), _as_decimal(pred)
        if g is not None and p is not None and g == p:
            return "correct_exact" if str(golden) == pred else "correct_normalized"
        return "wrong_value"

    if field == "vendor_name":
        aliases = golden if isinstance(golden, list) else [golden]
        pred_folded = fold_text(pred)
        for alias in aliases:
            alias_folded = fold_text(str(alias))
            if alias_folded == pred_folded:
                return "correct_exact" if str(alias) == pred else "correct_normalized"
            if alias_folded in pred_folded or pred_folded in alias_folded:
                return "correct_normalized"
        return "wrong_value"

    if field == "service_address":
        # golden holds a distinctive substring of the true address; punctuation
        # is stripped on both sides so "St." vs "St" or comma placement can't fail it
        if _loose(str(golden)) in _loose(pred):
            return "correct_normalized"
        return "wrong_value"

    if str(golden) == pred:
        return "correct_exact"
    if fold_text(str(golden)) == fold_text(pred):
        return "correct_normalized"
    return "wrong_value"


def load_golden(path: Path) -> dict[tuple[str, str], dict]:
    """-> {(source_file, utility_type): {field: golden_value}}"""
    data = yaml.safe_load(path.read_text(encoding="utf-8"))
    golden: dict[tuple[str, str], dict] = {}
    for entry in data["files"]:
        for row in entry["rows"]:
            key = (entry["file"], row["utility_type"] or "")
            golden[key] = {**row, "language": entry.get("language", "?")}
    return golden


def load_predictions(path: Path) -> dict[tuple[str, str], dict]:
    with path.open(encoding="utf-8-sig") as handle:
        rows = list(csv.DictReader(handle))
    return {(r["source_file"], r["utility_type"] or ""): r for r in rows}


def score(golden: dict[tuple[str, str], dict], predictions: dict[tuple[str, str], dict]) -> dict:
    per_field: dict[str, Counter] = defaultdict(Counter)
    per_language: dict[str, Counter] = defaultdict(Counter)
    row_issues: list[str] = []
    judged_files = {file for file, _ in golden}
    predicted_files = {file for file, _ in predictions}
    skipped_files = sorted({f for f in judged_files if f not in predicted_files})

    for key, gold in golden.items():
        if key[0] not in predicted_files:
            continue  # file wasn't part of this run (e.g. edge cases) — not a miss
        pred = predictions.get(key)
        if pred is None:
            row_issues.append(f"missing predicted row for {key[0]} [{key[1]}]")
            for field in EVAL_FIELDS:
                if field != "utility_type":
                    per_field[field]["missing_wrong"] += 1
                    per_language[gold["language"]]["missing_wrong"] += 1
            continue
        for field in EVAL_FIELDS:
            if field == "utility_type":
                continue  # it is the row key; a mismatch shows up as a missing row
            verdict = classify(field, gold.get(field), pred.get(field, ""))
            per_field[field][verdict] += 1
            per_language[gold["language"]][verdict] += 1

    for key in predictions:
        if key[0] in judged_files and key not in golden:
            row_issues.append(f"spurious predicted row {key[0]} [{key[1]}]")

    return {
        "per_field": per_field,
        "per_language": per_language,
        "row_issues": row_issues,
        "skipped_files": skipped_files,
    }


def _accuracy(counter: Counter) -> float:
    total = sum(counter.values())
    return (sum(counter[v] for v in ACCURATE) / total * 100) if total else 0.0


def render_report(results: dict, pred_path: Path, compare: tuple[Path, dict] | None) -> str:
    lines = ["# Extraction accuracy report", ""]
    lines.append(f"Predictions: `{pred_path.name}` · scored fields: {len(EVAL_FIELDS) - 1} per row")
    lines.append("")

    def field_table(res: dict) -> list[str]:
        out = [
            "| Field | N | Exact | Norm. | Missing ✓ | Missing ✗ | Halluc. | Wrong | Accuracy |",
            "|---|---|---|---|---|---|---|---|---|",
        ]
        overall: Counter = Counter()
        for field in EVAL_FIELDS:
            if field == "utility_type":
                continue
            c = res["per_field"][field]
            overall.update(c)
            out.append(
                f"| {field} | {sum(c.values())} | {c['correct_exact']} | "
                f"{c['correct_normalized']} | {c['missing_correct']} | {c['missing_wrong']} | "
                f"{c['hallucinated']} | {c['wrong_value']} | {_accuracy(c):.1f}% |"
            )
        out.append(
            f"| **overall** | {sum(overall.values())} | {overall['correct_exact']} | "
            f"{overall['correct_normalized']} | {overall['missing_correct']} | "
            f"{overall['missing_wrong']} | {overall['hallucinated']} | "
            f"{overall['wrong_value']} | **{_accuracy(overall):.1f}%** |"
        )
        return out

    lines += field_table(results)
    lines += [
        "",
        "## By language",
        "",
        "| Language | Field judgments | Accuracy |",
        "|---|---|---|",
    ]
    for lang in sorted(results["per_language"]):
        c = results["per_language"][lang]
        lines.append(f"| {lang} | {sum(c.values())} | {_accuracy(c):.1f}% |")

    if results["row_issues"]:
        lines += ["", "## Row-level issues", ""]
        lines += [f"- {issue}" for issue in results["row_issues"]]

    if results.get("skipped_files"):
        lines += ["", "_Labeled but not part of this run: "]
        lines[-1] += ", ".join(f"`{f}`" for f in results["skipped_files"]) + "_"

    if compare:
        cmp_path, cmp_results = compare
        overall_a = Counter()
        overall_b = Counter()
        for field in EVAL_FIELDS:
            if field != "utility_type":
                overall_a.update(results["per_field"][field])
                overall_b.update(cmp_results["per_field"][field])
        lines += [
            "",
            "## Provider comparison",
            "",
            "| CSV | Overall accuracy |",
            "|---|---|",
            f"| `{pred_path.name}` | {_accuracy(overall_a):.1f}% |",
            f"| `{cmp_path.name}` | {_accuracy(overall_b):.1f}% |",
        ]
    lines.append("")
    return "\n".join(lines)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="invoice-eval", description=__doc__)
    parser.add_argument("--pred", default=str(config.OUTPUTS_DIR / "invoices.csv"))
    parser.add_argument("--golden", default=str(config.GOLDEN_LABELS))
    parser.add_argument(
        "--compare", default=None, help="second CSV (e.g. the other provider) to score alongside"
    )
    parser.add_argument("-o", "--output", default=str(config.OUTPUTS_DIR / "eval_report.md"))
    parser.add_argument(
        "--min-accuracy",
        type=float,
        default=None,
        help="exit non-zero if overall accuracy falls below this percentage (regression gate)",
    )
    args = parser.parse_args(argv)

    golden = load_golden(Path(args.golden))
    results = score(golden, load_predictions(Path(args.pred)))

    compare = None
    if args.compare and Path(args.compare).exists():
        compare = (Path(args.compare), score(golden, load_predictions(Path(args.compare))))

    report = render_report(results, Path(args.pred), compare)
    out_path = Path(args.output)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(report, encoding="utf-8")
    print(report)
    print(f"written: {out_path}", file=sys.stderr)

    overall = Counter()
    for field in EVAL_FIELDS:
        if field != "utility_type":
            overall.update(results["per_field"][field])
    if args.min_accuracy is not None and _accuracy(overall) < args.min_accuracy:
        print(
            f"FAIL: accuracy {_accuracy(overall):.1f}% < gate {args.min_accuracy}%",
            file=sys.stderr,
        )
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

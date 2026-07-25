"""Command-line entrypoint.

invoice-extract samples -o outputs/invoices.csv                # live (Claude)
invoice-extract samples --provider openai -o out.csv           # live (OpenAI)
invoice-extract samples --mock                                 # offline replay, $0
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from . import config
from .csv_writer import write_rows
from .pipeline import build_run_report, run_pipeline, write_details
from .providers import get_provider


def make_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="invoice-extract",
        description="Extract structured data from multilingual utility invoices via an LLM.",
    )
    parser.add_argument(
        "inputs",
        nargs="*",
        default=[str(config.SAMPLES_DIR)],
        help="PDF/TXT files or directories (default: samples/)",
    )
    parser.add_argument(
        "-o", "--output", default=str(config.OUTPUTS_DIR / "invoices.csv"), help="output CSV path"
    )
    parser.add_argument(
        "--provider", choices=["anthropic", "openai"], default="anthropic", help="LLM provider"
    )
    parser.add_argument(
        "--mock",
        action="store_true",
        help="replay committed fixtures instead of calling the API (no key, no cost)",
    )
    parser.add_argument(
        "--vision",
        choices=["auto", "off"],
        default="auto",
        help="auto: retry image-only PDFs through the model's native PDF input (default)",
    )
    parser.add_argument(
        "--edge-cases", action="store_true", help="also process samples/edge_cases/"
    )
    parser.add_argument(
        "--no-fixtures", action="store_true", help="do not record fixtures on live runs"
    )
    parser.add_argument("-q", "--quiet", action="store_true", help="suppress per-file progress")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = make_parser().parse_args(argv)
    from .ingest import discover  # deferred: keeps --help snappy

    files = discover([Path(p) for p in args.inputs], include_edge_cases=args.edge_cases)
    if not files:
        print("no PDF/TXT documents found", file=sys.stderr)
        return 2

    provider = get_provider(args.provider, mock=args.mock)
    mode_label = f"{provider.name}" + ("" if args.mock else f" ({getattr(provider, 'model', '')})")
    print(f"Extracting {len(files)} document(s) via {mode_label}\n")

    summary = run_pipeline(
        files,
        provider,
        vision=args.vision,
        record_fixtures=not args.no_fixtures,
        verbose=not args.quiet,
    )

    csv_path = write_rows(summary.rows, Path(args.output))
    write_details(summary, config.OUTPUTS_DIR / "details")
    report = build_run_report(summary, csv_path)
    report_path = config.OUTPUTS_DIR / "run_report.json"
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")

    counts = report["row_status_counts"]
    print(
        f"\n{report['files']} file(s) -> {report['rows']} row(s) "
        f"[ok={counts.get('ok', 0)} review={counts.get('review', 0)} "
        f"failed={counts.get('failed', 0)}] "
        f"languages={','.join(report['languages'])}"
    )
    if not summary.mock:
        print(
            f"tokens {report['input_tokens']:,} in / {report['output_tokens']:,} out · "
            f"${report['cost_usd']:.4f} total (${report['cost_per_invoice_usd']:.4f}/invoice) · "
            f"{report['wall_s']}s"
        )
    print(f"CSV: {csv_path}\nReport: {report_path}")
    return 0 if counts.get("failed", 0) < report["files"] else 1


if __name__ == "__main__":
    raise SystemExit(main())

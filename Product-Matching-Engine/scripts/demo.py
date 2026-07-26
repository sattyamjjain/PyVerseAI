"""Predict products for a handful of requirements and print the matches.

Run: .venv/bin/python scripts/demo.py            # 3 built-in example tender lines
     .venv/bin/python scripts/demo.py --n 5      # first N rows of the labeled set
"""
import argparse
import os
import sys

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pandas as pd  # noqa: E402

from src.load_data import load_products, load_requirements  # noqa: E402
from src.tasks import predict_product_id  # noqa: E402

EXAMPLES = [
    (
        "Tiefspül-WC Duravit Starck 3 - Rimless",
        "Spülrandloses Wand-WC, wandhängend, Abmessungen (BxTxH) 360x540x340mm, "
        "Farbe weiß. Hersteller / Typ: Duravit / Starck 3",
    ),
    (
        "WC-Sitz mit Absenkautomatik",
        "WC-Sitz weiß mit Edelstahlscharnieren und Absenkautomatik, passend zu Starck 3.",
    ),
    (
        "Waschtisch 600 x 460 mm",
        "Waschtisch mit Hahnloch und Überlauf, wandhängend, Duravit ME by Starck, weiß.",
    ),
]


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--n", type=int, default=None, help="use first N labeled rows instead")
    args = parser.parse_args()

    if args.n:
        rows = load_requirements().head(args.n)
        df = rows[["requirement", "requirement_detail"]]
        truth = rows["product_id"].tolist()
    else:
        df = pd.DataFrame(EXAMPLES, columns=["requirement", "requirement_detail"])
        truth = None

    catalog = load_products().set_index("product_id")
    for i, pid in enumerate(predict_product_id(df)):
        name = catalog.loc[pid, "name"] if pid in catalog.index else "<unknown>"
        print(f"\n[{i + 1}] {str(df.iloc[i]['requirement']).strip()[:80]}")
        print(f"    -> {pid}  {name}")
        if truth:
            print(f"    truth: {truth[i]}  {'HIT' if pid == truth[i] else 'MISS'}")


if __name__ == "__main__":
    main()

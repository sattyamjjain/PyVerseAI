"""Experiment 01 — data profiling that shaped the whole approach.

Findings (run to reproduce):
- 2,180 products / 1,000 requirements, all targets present in catalog
- only 318 unique target products; top target appears 38x, 158 appear once
- 171 duplicate (requirement, detail) pairs -> eval splits must be group-aware
- 236 rows contain the exact target article number in the text ("#2527090000",
  "Bestellnummer: ...") -> deterministic extraction is the strongest single signal
- 264 rows contain ANY catalog id; in 225 of them the target is among the extracted
- German tender language: 259 rows say "gleichwertig", 636 name "Duravit",
  514 contain dimension strings like "600 x 460"
"""
import os
import re
import sys

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.load_data import load_products, load_requirements  # noqa: E402

prods = load_products()
reqs = load_requirements()
text = (reqs["requirement"].fillna("") + " " + reqs["requirement_detail"].fillna(""))

print("products:", prods.shape, "| requirements:", reqs.shape)
print("nulls:", {"requirement": int(reqs["requirement"].isna().sum()),
                 "requirement_detail": int(reqs["requirement_detail"].isna().sum())})
print("unique targets:", reqs["product_id"].nunique(),
      "| all targets in catalog:", bool(reqs["product_id"].isin(prods["product_id"]).all()))
print("duplicate (req, detail) pairs:", int(reqs.duplicated(["requirement", "requirement_detail"]).sum()))

vc = reqs["product_id"].value_counts()
print("top-5 targets:", vc.head(5).to_dict(), "| singleton targets:", int((vc == 1).sum()))

catalog_ids = set(prods["product_id"])
extracted = text.map(lambda x: [t for t in re.findall(r"\d{7,}", x) if t in catalog_ids])
has_any = extracted.str.len() > 0
target_in = [t in ids for t, ids in zip(reqs["product_id"], extracted)]
print("rows with any catalog id in text:", int(has_any.sum()),
      "| target among extracted:", int(sum(a and b for a, b in zip(has_any, target_in))))
print("rows with exact target id in text:",
      int(sum(str(t) in x for t, x in zip(reqs["product_id"], text))))

low = text.str.lower()
for marker in ["gleichwertig", "bestellnummer", "duravit", "rimless", "starck"]:
    print(f"rows mentioning '{marker}':", int(low.str.contains(marker).sum()))
print("rows with dimension pattern (NxM):", int(low.str.contains(r"\d+\s*x\s*\d+").sum()))

print("\nproduct categories:", prods["category"].value_counts().to_dict())
print("\ntarget categories:",
      reqs.merge(prods, on="product_id")["category"].value_counts().to_dict())
print("\nid length distribution (catalog):", prods["product_id"].str.len().value_counts().to_dict())

"""CSV output.

utf-8-sig on purpose: Excel renders bare-UTF-8 'Québec' as 'QuÃ©bec'; the BOM
fixes it and every other consumer ignores it. Rows are sorted so identical
inputs always produce byte-identical files (the mock-replay guarantee).
"""

from __future__ import annotations

import csv
from pathlib import Path

from .schema import CSV_COLUMNS, InvoiceRow


def write_rows(rows: list[InvoiceRow], path: Path) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    ordered = sorted(rows, key=lambda r: (r.source_file, r.utility_type or ""))
    with path.open("w", newline="", encoding="utf-8-sig") as handle:
        writer = csv.DictWriter(handle, fieldnames=CSV_COLUMNS)
        writer.writeheader()
        for row in ordered:
            writer.writerow(row.as_csv_dict())
    return path

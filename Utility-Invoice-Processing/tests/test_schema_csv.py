from __future__ import annotations

import csv
import json

from conftest import make_extraction

from invoice_extractor.csv_writer import write_rows
from invoice_extractor.schema import CSV_COLUMNS, InvoiceExtraction, InvoiceRow

ASSESSMENT_FIELDS = [
    "vendor_name",
    "invoice_date",
    "service_address",
    "utility_type",
    "usage_amount",
    "usage_unit",
    "billing_period_start",
    "billing_period_end",
]


def test_csv_columns_lead_with_the_assessment_fields_in_order():
    assert CSV_COLUMNS[: len(ASSESSMENT_FIELDS)] == ASSESSMENT_FIELDS


def test_extraction_schema_roundtrips_through_json():
    extraction = make_extraction()
    restored = InvoiceExtraction.model_validate(json.loads(extraction.model_dump_json()))
    assert restored == extraction


def test_all_null_extraction_validates():
    """The model must be able to say 'nothing found' without breaking schema."""
    payload = {
        "document_type": "other",
        "language": None,
        "currency": None,
        "vendor_name": {"source_quote": None, "value": None, "status": "not_found"},
        "invoice_date": {"source_quote": None, "value": None, "status": "not_found"},
        "service_address": {"source_quote": None, "value": None, "status": "not_found"},
        "total_amount": {"source_quote": None, "value": None, "status": "not_found"},
        "readings": [],
        "notes": None,
    }
    extraction = InvoiceExtraction.model_validate(payload)
    assert extraction.vendor_name.value is None
    assert extraction.readings == []


def test_write_rows_bom_header_and_sorting(tmp_path):
    rows = [
        InvoiceRow(source_file="b.pdf", utility_type="gas", usage_amount="83.9"),
        InvoiceRow(source_file="a.pdf", utility_type="electricity", usage_amount="458"),
        InvoiceRow(source_file="b.pdf", utility_type="electricity"),
    ]
    path = write_rows(rows, tmp_path / "out.csv")

    raw = path.read_bytes()
    assert raw.startswith(b"\xef\xbb\xbf"), "utf-8-sig BOM required for Excel"

    with path.open(encoding="utf-8-sig") as handle:
        parsed = list(csv.DictReader(handle))
    assert [r["source_file"] for r in parsed] == ["a.pdf", "b.pdf", "b.pdf"]
    assert [r["utility_type"] for r in parsed] == ["electricity", "electricity", "gas"]
    assert list(parsed[0].keys()) == CSV_COLUMNS
    assert parsed[0]["usage_amount"] == "458"
    assert parsed[2]["usage_amount"] == "83.9"
    assert parsed[2]["vendor_name"] == ""  # None -> empty cell, never the string 'None'

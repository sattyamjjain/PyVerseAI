"""Pipeline post-processing tests: synthetic extractions through the real
deterministic half (quote verification, normalization, flags, row shaping)."""

from __future__ import annotations

from conftest import SAMPLE_TEXT, make_doc, make_extraction, make_reading, make_result

from invoice_extractor.pipeline import postprocess
from invoice_extractor.schema import FieldStatus, UsageSource, UtilityType


def test_clean_extraction_yields_ok_row():
    rows, detail = postprocess(make_result(make_extraction()), make_doc())
    assert len(rows) == 1
    row = rows[0]
    assert row.extraction_status == "ok"
    assert row.validation_flags == ""
    assert row.vendor_name == "ACME Power & Light Company"
    assert row.invoice_date == "2026-06-15"
    assert row.utility_type == "electricity"
    assert row.usage_amount == "458"
    assert row.usage_unit == "kWh"
    assert row.billing_period_start == "2026-05-12"
    assert row.billing_period_end == "2026-06-11"
    assert row.total_amount == "92.15"
    assert detail["fields"]["vendor_name"]["quote_verified"] is True


def test_fabricated_quote_is_caught_and_demotes_row():
    """The hallucination filter: a value whose 'evidence' is not in the
    document gets flagged no matter how confident the model claimed to be."""
    extraction = make_extraction(
        vendor_name={
            "value": "Springfield Electric Co-op",
            "source_quote": "Springfield Electric Co-op — your trusted partner",
            "status": "confident",
        }
    )
    rows, detail = postprocess(make_result(extraction), make_doc())
    assert "quote_unverified_vendor_name" in rows[0].validation_flags
    assert rows[0].extraction_status == "review"
    assert detail["fields"]["vendor_name"]["quote_verified"] is False


def test_combined_bill_yields_one_row_per_commodity():
    extraction = make_extraction(
        readings=[
            make_reading(),
            make_reading(
                utility_type=UtilityType.GAS,
                usage_quote="Total Gas you used in Therms: 83.9",
                usage_amount_raw="83.9",
                usage_unit_raw="Therms",
            ),
        ]
    )
    rows, _ = postprocess(make_result(extraction), make_doc())
    assert [r.utility_type for r in rows] == ["electricity", "gas"]
    assert rows[1].usage_amount == "83.9"
    assert rows[1].usage_unit == "therms"
    assert all(r.source_file == "acme-test.pdf" for r in rows)


def test_localized_number_and_date_normalization_flow():
    text = (
        "Iberdrola Clientes S.A.U.\n"
        "Periodo de facturación: del 08/05/2018 a 10/06/2018\n"
        "Consumo del periodo: 222,45 kWh\n"
    )
    extraction = make_extraction(
        language="es",
        vendor_name={
            "value": "Iberdrola Clientes S.A.U.",
            "source_quote": "Iberdrola Clientes S.A.U.",
            "status": "confident",
        },
        invoice_date={"value": None, "source_quote": None, "status": "not_found"},
        service_address={"value": None, "source_quote": None, "status": "not_found"},
        total_amount={"value": None, "source_quote": None, "status": "not_found"},
        readings=[
            make_reading(
                usage_quote="Consumo del periodo: 222,45 kWh",
                usage_amount_raw="222,45",
                usage_unit_raw="kWh",
                period_quote="Periodo de facturación: del 08/05/2018 a 10/06/2018",
                billing_period_start="2018-05-08",
                billing_period_end="2018-06-10",
            )
        ],
    )
    rows, _ = postprocess(make_result(extraction), make_doc(text, "iberdrola.pdf"))
    row = rows[0]
    assert row.usage_amount == "222.45"
    assert row.billing_period_start == "2018-05-08"
    assert row.billing_period_end == "2018-06-10"
    assert "date_crosscheck_failed_period_start" not in row.validation_flags


def test_day_month_swap_is_caught_by_crosscheck():
    text = "Periodo: del 08/05/2018 a 10/06/2018\nConsumo: 222,45 kWh\n"
    extraction = make_extraction(
        language="es",
        readings=[
            make_reading(
                usage_quote="Consumo: 222,45 kWh",
                usage_amount_raw="222,45",
                period_quote="Periodo: del 08/05/2018 a 10/06/2018",
                billing_period_start="2018-08-05",  # swapped day/month
                billing_period_end="2018-06-10",
            )
        ],
    )
    rows, _ = postprocess(make_result(extraction), make_doc(text))
    assert "date_crosscheck_failed_period_start" in rows[0].validation_flags
    assert rows[0].extraction_status == "review"


def test_not_found_usage_on_consumption_invoice_needs_review():
    extraction = make_extraction(
        readings=[
            make_reading(
                usage_quote=None,
                usage_amount_raw=None,
                usage_unit_raw=None,
                usage_source=UsageSource.NOT_FOUND,
                usage_status=FieldStatus.NOT_FOUND,
            )
        ]
    )
    rows, _ = postprocess(make_result(extraction), make_doc())
    assert rows[0].usage_amount is None
    assert rows[0].extraction_status == "review"


def test_no_readings_still_produces_an_accounting_row():
    rows, _ = postprocess(make_result(make_extraction(readings=[])), make_doc())
    assert len(rows) == 1
    assert rows[0].utility_type is None
    assert "no_readings" in rows[0].validation_flags


def test_vision_mode_skips_quote_verification_but_flags_it():
    extraction = make_extraction(
        vendor_name={
            "value": "ACME Power & Light Company",
            "source_quote": "something the vision model read off the image",
            "status": "confident",
        }
    )
    rows, _ = postprocess(make_result(extraction, mode="vision"), make_doc(SAMPLE_TEXT))
    assert "vision_mode_quotes_unverifiable" in rows[0].validation_flags
    assert "quote_unverified_vendor_name" not in rows[0].validation_flags

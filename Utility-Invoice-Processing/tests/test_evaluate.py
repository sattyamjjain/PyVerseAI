"""The eval harness itself must be trustworthy — its taxonomy is the report."""

from __future__ import annotations

from invoice_extractor import config
from invoice_extractor.evaluate import EVAL_FIELDS, classify, load_golden, score


def test_taxonomy_missing_and_hallucination_semantics():
    assert classify("usage_amount", None, "") == "missing_correct"
    assert classify("usage_amount", None, "800") == "hallucinated"
    assert classify("usage_amount", "458", "") == "missing_wrong"
    assert classify("usage_amount", "458", "521") == "wrong_value"


def test_numbers_match_by_value_not_formatting():
    assert classify("usage_amount", "48469", "48469") == "correct_exact"
    assert classify("usage_amount", "83.9", "83.90") == "correct_normalized"
    assert classify("usage_amount", "6.40", "6.4") == "correct_normalized"


def test_vendor_aliases_and_substring_leniency():
    golden = ["Central Hudson", "Central Hudson Gas & Electric"]
    assert classify("vendor_name", golden, "Central Hudson") == "correct_exact"
    assert (
        classify("vendor_name", golden, "Central Hudson Gas & Electric Corporation")
        == "correct_normalized"
    )
    assert classify("vendor_name", golden, "ESCO NAME") == "wrong_value"


def test_address_matching_ignores_punctuation_and_case():
    assert (
        classify("service_address", "123 Main St", "123 MAIN ST., NEENAH WI 54956")
        == "correct_normalized"
    )
    assert classify("service_address", "525 Golden Gate Ave", "PO Box 7369") == "wrong_value"


def test_dates_and_units_match_exactly_or_folded():
    assert classify("billing_period_start", "2026-01-05", "2026-01-05") == "correct_exact"
    assert classify("billing_period_start", "2026-01-05", "2026-05-01") == "wrong_value"
    assert classify("usage_unit", "kWh", "kWh") == "correct_exact"
    assert classify("usage_unit", "therms", "Therms") == "correct_normalized"


def test_committed_golden_labels_load_and_cover_the_sample_set():
    golden = load_golden(config.GOLDEN_LABELS)
    files = {file for file, _ in golden}
    for expected in [
        "centralhudson-us-electric-en.pdf",
        "weenergies-us-electric-gas-en.pdf",
        "sfpuc-us-water-en.pdf",
        "exodo-es-electricity-es.pdf",
        "vialis-fr-electricity-fr.pdf",
        "swm-de-electricity-de.pdf",
        "edf-fr-electricity-fr.pdf",
    ]:
        assert expected in files
    # combined bills carry one row per commodity
    assert ("weenergies-us-electric-gas-en.pdf", "gas") in golden
    assert ("sfpuc-us-water-en.pdf", "sewer") in golden
    # every golden row labels every scored field
    for row in golden.values():
        for field in EVAL_FIELDS:
            assert field in row, f"{row.get('utility_type')} row missing {field}"


def test_score_skips_files_absent_from_the_run():
    golden = {
        ("a.pdf", "electricity"): {
            "language": "en",
            "usage_amount": "1",
            "utility_type": "electricity",
        },
        ("b.pdf", "electricity"): {
            "language": "en",
            "usage_amount": "2",
            "utility_type": "electricity",
        },
    }
    predictions = {("a.pdf", "electricity"): {"usage_amount": "1", "source_file": "a.pdf"}}
    results = score(golden, predictions)
    assert results["skipped_files"] == ["b.pdf"]
    total = sum(sum(c.values()) for c in results["per_field"].values())
    assert total > 0  # a.pdf judged; b.pdf contributed nothing rather than misses

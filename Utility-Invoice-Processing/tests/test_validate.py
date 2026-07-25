from __future__ import annotations

from datetime import date
from decimal import Decimal

from invoice_extractor.normalize import fold_text
from invoice_extractor.validate import reading_flags, verify_quote

TODAY = date(2026, 7, 25)


def flags(**kwargs) -> list[str]:
    defaults = dict(
        usage_amount=Decimal("458"),
        usage_unit="kWh",
        period_start=date(2026, 5, 12),
        period_end=date(2026, 6, 11),
        invoice_date=date(2026, 6, 15),
        today=TODAY,
    )
    defaults.update(kwargs)
    return reading_flags(**defaults)


def test_clean_reading_has_no_flags():
    assert flags() == []


def test_reversed_period_flagged():
    # the lapalma sample really prints 31/05/2024 -> 22/06/2021
    result = flags(period_start=date(2024, 5, 31), period_end=date(2021, 6, 22))
    assert "period_reversed" in result


def test_period_longer_than_400_days_flagged():
    assert "period_gt_400_days" in flags(
        period_start=date(2020, 1, 1), period_end=date(2021, 6, 1), invoice_date=None
    )


def test_annual_german_reconciliation_not_flagged():
    result = flags(
        usage_amount=Decimal("7140"),
        period_start=date(2022, 1, 1),
        period_end=date(2022, 12, 31),
        invoice_date=date(2023, 1, 15),
    )
    assert result == []


def test_future_period_end_flagged():
    assert "future_period_end" in flags(
        period_start=date(2026, 7, 1), period_end=date(2026, 9, 1), invoice_date=None
    )


def test_invoice_date_before_period_end_flagged():
    assert "invoice_predates_period_end" in flags(invoice_date=date(2026, 6, 1))


def test_negative_usage_flagged_not_rejected():
    # solar net metering legitimately produces negative net consumption
    result = flags(usage_amount=Decimal("-120"))
    assert "negative_usage" in result


def test_zero_usage_is_legitimate():
    # vacant property: standing charges, zero consumption — no flag
    assert flags(usage_amount=Decimal("0")) == []


def test_thousandfold_understatement_caught_by_magnitude_band():
    # German '7.140' kWh misparsed under a US locale as 7.140 -> 0.02 kWh/day
    result = flags(
        usage_amount=Decimal("7.140"),
        period_start=date(2022, 1, 1),
        period_end=date(2022, 12, 31),
        invoice_date=date(2023, 1, 15),
    )
    assert "usage_magnitude_suspect" in result


def test_unknown_unit_skips_magnitude_check():
    assert flags(usage_unit="frobnicate") == []


def test_verify_quote_tolerates_whitespace_and_case():
    doc = fold_text("Total electricity  you\nused: 458 kWh")
    assert verify_quote("Total electricity you used: 458 kWh", doc)
    assert verify_quote("total ELECTRICITY you used", doc)


def test_verify_quote_is_space_insensitive_both_directions():
    # model stripped spaces while quoting
    doc = fold_text("284 SOUTH AVENUE\nPOUGHKEEPSIE NY 12601-4839")
    assert verify_quote("284SOUTHAVENUE POUGHKEEPSIENY12601-4839", doc)
    # extractor merged words the model quoted faithfully
    doc = fold_text("CurrentBillingPeriod May25,2021-Jun22,2021")
    assert verify_quote("Current Billing Period May 25, 2021 - Jun 22, 2021", doc)


def test_verify_quote_rejects_absent_text():
    doc = fold_text("Some completely different document")
    assert not verify_quote("Total electricity you used: 458 kWh", doc)
    assert not verify_quote(None, doc)
    assert not verify_quote("   ", doc)

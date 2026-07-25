"""The normalization layer is where multilingual invoices actually break;
every historical failure mode from the research gets a case here."""

from __future__ import annotations

from datetime import date
from decimal import Decimal

import pytest

from invoice_extractor.normalize import (
    crosscheck_date,
    fold_text,
    normalize_unit,
    parse_iso_date,
    parse_localized_number,
)


@pytest.mark.parametrize(
    ("raw", "language", "expected"),
    [
        # French: space as thousands separator — ASCII, NBSP and narrow NBSP all occur
        ("48 469", "fr", Decimal("48469")),
        ("48 469", "fr", Decimal("48469")),
        ("48 469", "fr", Decimal("48469")),
        ("1 234,56", "fr", Decimal("1234.56")),
        # German: dot-thousands, comma-decimal — the 1000x trap
        ("7.140", "de", Decimal("7140")),
        ("2.157,5", "de", Decimal("2157.5")),
        ("1.234.567", "de", Decimal("1234567")),
        ("0,00", "de", Decimal("0")),
        ("-671,06", "de", Decimal("-671.06")),  # credit note / Guthaben
        # Spanish
        ("222,45", "es", Decimal("222.45")),
        ("1.234,56", "es", Decimal("1234.56")),
        # US/UK
        ("83.9", "en", Decimal("83.9")),
        ("1,234.56", "en", Decimal("1234.56")),
        ("1,234", "en", Decimal("1234")),
        ("598,800", "en", Decimal("598800")),
        ("458", "en", Decimal("458")),
        ("0", "en", Decimal("0")),
        # Indian lakh grouping — survives because period-decimal strips all commas
        ("5,67,780.22", "en", Decimal("567780.22")),
        # Swiss apostrophes (both ASCII and typographic)
        ("1'234.56", None, Decimal("1234.56")),
        ("1’234.56", None, Decimal("1234.56")),
        # No locale prior: sensible heuristics
        ("222,45", None, Decimal("222.45")),  # 2 trailing digits -> decimal
        ("1,234", None, Decimal("1234")),  # exactly 3 trailing digits -> grouping
        ("1.234", None, Decimal("1234")),
        ("83.95", None, Decimal("83.95")),
        # Stray unit/currency characters survive
        ("458 kWh", "en", Decimal("458")),
        ("$92.15", "en", Decimal("92.15")),
        ("  458  ", "en", Decimal("458")),
        # Missing-value tokens -> None, never 0
        ("N/A", "en", None),
        ("", "en", None),
        ("--", None, None),
        ("abc", None, None),
        (None, "en", None),
    ],
)
def test_parse_localized_number(raw, language, expected):
    assert parse_localized_number(raw, language) == expected


@pytest.mark.parametrize(
    ("raw", "canonical", "flag"),
    [
        ("kWh", "kWh", None),
        ("kwh", "kWh", None),
        ("KWH", "kWh", None),
        ("Kilowattstunden", "kWh", None),
        ("m³", "m3", None),  # NFKC folds the superscript
        ("m3", "m3", None),
        ("Kubikmeter", "m3", None),
        ("therms", "therms", None),
        ("Therm", "therms", None),
        ("thm", "therms", None),
        ("CCF", "CCF", None),
        ("ccf", "CCF", None),
        ("HCF", "HCF", None),
        ("gallons", "gallons", None),
        ("Gallon", "gallons", None),
        ("litres", "litres", None),
        ("MWh", "MWh", None),
        ("kWh.", "kWh", None),
        # SFPUC-style "units" is real but ambiguous without the bill's own legend
        ("units", "units", "ambiguous_unit"),
        # demand/power units must never pass silently as consumption
        ("kW", "kW", "demand_unit_as_usage"),
        ("kVA", "kVA", "demand_unit_as_usage"),
        # unknown units are preserved but flagged, never guessed
        ("frobnicate", "frobnicate", "unknown_unit"),
        (None, None, None),
        ("   ", None, None),
    ],
)
def test_normalize_unit(raw, canonical, flag):
    assert normalize_unit(raw) == (canonical, flag)


@pytest.mark.parametrize(
    ("value", "expected"),
    [
        ("2018-05-08", date(2018, 5, 8)),
        (" 2021-06-23 ", date(2021, 6, 23)),
        ("00/00/0000", None),
        ("2018-13-40", None),
        ("not a date", None),
        ("", None),
        (None, None),
    ],
)
def test_parse_iso_date(value, expected):
    assert parse_iso_date(value) == expected


@pytest.mark.parametrize(
    ("iso", "quote", "language", "expect_flag"),
    [
        # agreement across locales -> no flag
        ("2018-05-08", "Periodo de facturación: del 08/05/2018 a 10/06/2018", "es", False),
        ("2021-05-25", "Current Billing Period: May 25, 2021 - Jun 22, 2021", "en", False),
        ("2023-07-01", "Abrechnungszeitraum ab 01.07.2023", "de", False),
        ("2026-02-02", "Bill Period: 01/05/2026 to 02/02/2026", "en", False),
        ("2019-02-11", "du 02/02/2019 au 11/02/2019", "fr", False),
        # the LLM swapped day/month -> caught
        ("2018-08-05", "Periodo de facturación: del 08/05/2018 a 10/06/2018", "es", True),
        # pdfplumber layout mode merges kerned words; both dates must still verify
        ("2021-05-25", "CurrentBillingPeriod May25,2021-Jun22,2021", "en", False),
        ("2021-06-22", "CurrentBillingPeriod May25,2021-Jun22,2021", "en", False),
        # ...and a real swap is still caught on mashed text
        ("2021-05-26", "CurrentBillingPeriod May25,2021-Jun22,2021", "en", True),
        # Spanish month-name date ("13 de junio de 2018")
        ("2018-06-13", "Fecha de emisión de factura 13 de junio de 2018", "es", False),
        # no independently parseable date in the quote -> no evidence, no flag
        ("2021-05-25", "as stated on your bill", "en", False),
        ("2021-05-25", None, "en", False),
        ("2021-05-25", "", "en", False),
        # unparsed value -> nothing to check
        (None, "May 25, 2021", "en", False),
    ],
)
def test_crosscheck_date(iso, quote, language, expect_flag):
    flag = crosscheck_date(iso, quote, language)
    assert (flag == "date_crosscheck_failed") is expect_flag


def test_fold_text_unifies_exotic_characters():
    # U+2011 non-breaking hyphen (Hydro-Québec's own name) folds to '-'
    assert fold_text("Hydro‑Québec") == "hydro-québec"
    # NBSP and newline runs collapse to single spaces; case folds
    assert fold_text("Total amount\n   DUE") == "total amount due"
    # NFKC folds superscripts, so m³ in quote matches m3 in text and vice versa
    assert fold_text("692 m³") == fold_text("692 m3")

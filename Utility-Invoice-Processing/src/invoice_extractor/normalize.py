"""Deterministic normalization: the code side of the LLM/code boundary.

The model returns values AS PRINTED plus verbatim quotes; everything here is a
pure function with exhaustive unit tests — which is the point of the split.
"""

from __future__ import annotations

import re
import unicodedata
from datetime import date
from decimal import Decimal, InvalidOperation

import dateparser
import dateparser.search

# Languages that write decimals with a comma (1.234,56 / 1 234,56).
COMMA_DECIMAL_LANGS = {"es", "fr", "de", "it", "pt", "nl", "ca", "da", "sv", "fi", "nb", "tr"}

# Day-first date order. "en" is genuinely ambiguous (UK=DMY, US=MDY); we default
# en -> MDY and rely on the cross-check + period-sanity flags to catch misreads.
DMY_LANGS = COMMA_DECIMAL_LANGS

# Thousands separators that appear BETWEEN digits: any whitespace flavour
# (French PDFs emit ASCII space, NBSP and narrow NBSP interchangeably -
# verified at byte level) plus Swiss apostrophes.
_BETWEEN_DIGITS_JUNK = re.compile(r"(?<=\d)[\s'\u2019\u2018](?=\d)")
_HYPHENS = dict.fromkeys([0x2010, 0x2011, 0x2012, 0x2013, 0x2014, 0x2015, 0x2212], "-")
_MISSING_TOKENS = {"", "n/a", "na", "none", "null", "-", "--"}


def fold_text(text: str) -> str:
    """Canonical form used for quote verification: NFKC, unified hyphens,
    all whitespace runs collapsed to single spaces, casefolded."""
    text = unicodedata.normalize("NFKC", text).translate(_HYPHENS)
    return re.sub(r"\s+", " ", text).casefold().strip()


def parse_localized_number(raw: str | None, language: str | None = None) -> Decimal | None:
    """Parse a number as printed anywhere in the world.

    Survives '48 469' (fr), '2.157,5' (de), '1'234.56' (ch), '5,67,780.22' (in),
    '1,234.56' (us) and '222,45' (es). Returns None rather than guessing.
    """
    if raw is None:
        return None
    s = unicodedata.normalize("NFKC", raw).strip()
    if s.casefold() in _MISSING_TOKENS:
        return None
    s = _BETWEEN_DIGITS_JUNK.sub("", s)
    s = re.sub(r"[^\d,.\-+]", "", s)  # drop stray currency/unit characters
    if not re.search(r"\d", s):
        return None

    has_comma, has_period = "," in s, "." in s
    if has_comma and has_period:
        # Whichever separator comes LAST is the decimal mark.
        if s.rfind(",") > s.rfind("."):
            s = s.replace(".", "").replace(",", ".")
        else:
            s = s.replace(",", "")  # also handles lakh grouping 5,67,780.22
    elif has_comma:
        s = _resolve_single_separator(s, ",", language)
    elif has_period:
        s = _resolve_single_separator(s, ".", language)
    try:
        return Decimal(s)
    except InvalidOperation:
        return None


def _resolve_single_separator(s: str, sep: str, language: str | None) -> str:
    """Decide whether the only separator present is decimal or grouping."""
    comma_decimal = (language in COMMA_DECIMAL_LANGS) if language else None
    is_decimal_mark = None if comma_decimal is None else (sep == ",") == comma_decimal
    if s.count(sep) > 1:
        is_decimal_mark = False  # "1.234.567" — repeated separator is always grouping
    elif is_decimal_mark is None:
        # No locale prior: a lone separator with exactly 3 trailing digits is
        # grouping ("1,234"), anything else is a decimal mark ("83.9", "222,45").
        is_decimal_mark = not re.search(rf"\{sep}\d{{3}}$", s)
    if is_decimal_mark:
        return s.replace(",", ".") if sep == "," else s
    return s.replace(sep, "")


# --- units -----------------------------------------------------------------

# Canonical labels only — values are NEVER converted between units (CCF->therms
# needs a per-utility, per-month heat factor; doing it "roughly" is silently wrong).
_UNIT_ALIASES: dict[str, str] = {
    "kwh": "kWh",
    "kilowatt hour": "kWh",
    "kilowatt-hour": "kWh",
    "kilowatt hours": "kWh",
    "kilowattstunden": "kWh",
    "kwh.": "kWh",
    "mwh": "MWh",
    "therm": "therms",
    "therms": "therms",
    "thm": "therms",
    "ccf": "CCF",
    "100 cubic feet": "CCF",
    "hundred cubic feet": "CCF",
    "hcf": "HCF",
    "m3": "m3",
    "m³": "m3",
    "cubic meter": "m3",
    "cubic meters": "m3",
    "cubic metre": "m3",
    "cubic metres": "m3",
    "kubikmeter": "m3",
    "metros cubicos": "m3",
    "mètres cubes": "m3",
    "gal": "gallons",
    "gallon": "gallons",
    "gallons": "gallons",
    "l": "litres",
    "litre": "litres",
    "litres": "litres",
    "liter": "litres",
    "liters": "litres",
    "unit": "units",
    "units": "units",  # e.g. SFPUC bills water in "units" (= CCF)
    "kw": "kW",
    "kva": "kVA",
    "kvar": "kVAr",  # demand/power — flagged by validators
}

DEMAND_UNITS = {"kW", "kVA", "kVAr"}
AMBIGUOUS_UNITS = {"units"}


def normalize_unit(raw: str | None) -> tuple[str | None, str | None]:
    """-> (canonical_or_cleaned_unit, flag_or_None)."""
    if raw is None or not raw.strip():
        return None, None
    key = unicodedata.normalize("NFKC", raw).strip().strip(".").casefold()
    canonical = _UNIT_ALIASES.get(key)
    if canonical is None:
        return raw.strip(), "unknown_unit"
    if canonical in DEMAND_UNITS:
        return canonical, "demand_unit_as_usage"
    if canonical in AMBIGUOUS_UNITS:
        return canonical, "ambiguous_unit"
    return canonical, None


# --- dates -----------------------------------------------------------------


def parse_iso_date(value: str | None) -> date | None:
    if not value:
        return None
    try:
        return date.fromisoformat(value.strip())
    except ValueError:
        return None


# Numeric date shapes: 08/05/2018, 01.07.2023, 2018-05-08, 5-6-18 ...
_NUMERIC_DATE = re.compile(r"\b\d{1,4}[./\-]\s?\d{1,2}[./\-]\s?\d{1,4}\b")


def crosscheck_date(iso_value: str | None, quote: str | None, language: str | None) -> str | None:
    """Re-derive the date from the verbatim quote with an independent parser
    (dateparser, locale-seeded) and compare. Returns a flag code or None.

    The LLM has whole-document context (locale cues) that dateparser lacks;
    dateparser has none of the LLM's failure modes. Agreement -> trust.
    Disagreement -> flag for review instead of silently picking a winner.

    Numeric tokens are regex-extracted and parsed individually because
    dateparser's own segmentation merges ranges like 'del 08/05/2018 a
    10/06/2018' into one garbage date under some locales.
    """
    parsed = parse_iso_date(iso_value)
    if parsed is None or not quote or not quote.strip():
        return None
    order = "DMY" if (language in DMY_LANGS) else "MDY"
    langs = [language] if language and len(language) == 2 else None
    settings = {"DATE_ORDER": order, "REQUIRE_PARTS": ["day", "month", "year"]}

    candidates: set[date] = set()
    for token in _NUMERIC_DATE.findall(quote):
        try:
            found = dateparser.parse(token, languages=langs, settings=settings)
        except Exception:
            found = None
        if found:
            candidates.add(found.date())
    if not candidates:  # month-name formats ("May 25, 2021", "25 juin 2021")
        try:
            found_all = dateparser.search.search_dates(quote, languages=langs, settings=settings)
        except Exception:
            found_all = None
        candidates.update(dt.date() for _, dt in (found_all or []))

    if not candidates:
        return None  # nothing independently parseable -> no evidence either way
    if parsed in candidates:
        return None
    return "date_crosscheck_failed"

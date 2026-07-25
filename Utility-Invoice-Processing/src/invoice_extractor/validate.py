"""Business-rule validation.

Hard schema failures are impossible by construction (server-side grammar
enforcement), so everything here is a SOFT check: rows are always written,
best-effort, and violations become codes in the `validation_flags` column that
route the row to human review. Thresholds follow published industry practice
(EnergyCAP bill-audit rules, ENERGY STAR data-quality checks).
"""

from __future__ import annotations

from datetime import date
from decimal import Decimal

from .normalize import fold_text

# Plausible consumption PER DAY by unit — deliberately generous bands whose only
# job is to catch order-of-magnitude errors (the classic 1000x locale misparse),
# which schema validation cannot see because the wrong number is well-typed.
DAILY_BANDS: dict[str, tuple[float, float]] = {
    "kWh": (0.05, 200_000),
    "MWh": (0.0001, 200),
    "therms": (0.01, 20_000),
    "CCF": (0.01, 20_000),
    "HCF": (0.01, 20_000),
    "units": (0.01, 20_000),
    "m3": (0.005, 50_000),
    "gallons": (0.5, 5_000_000),
    "litres": (2, 20_000_000),
}


def verify_quote(quote: str | None, folded_document: str) -> bool:
    """A value is only as trustworthy as its evidence: the model's verbatim
    quote must actually appear in the document text (whitespace/case folded).
    If it does not, the field is treated as unverified regardless of status."""
    if not quote or not quote.strip():
        return False
    return fold_text(quote) in folded_document


def reading_flags(
    *,
    usage_amount: Decimal | None,
    usage_unit: str | None,
    period_start: date | None,
    period_end: date | None,
    invoice_date: date | None,
    today: date | None = None,
) -> list[str]:
    """Cross-field sanity checks for one commodity reading."""
    today = today or date.today()
    flags: list[str] = []
    days: int | None = None

    if period_start and period_end:
        days = (period_end - period_start).days
        if days < 0:
            flags.append("period_reversed")
        elif days > 400:
            flags.append("period_gt_400_days")
    if period_end and period_end > today:
        flags.append("future_period_end")
    if invoice_date and period_end and invoice_date < period_end and "period_reversed" not in flags:
        # Statement date normally falls on/after period end; earlier usually
        # means a day/month order misparse somewhere.
        flags.append("invoice_predates_period_end")

    if usage_amount is not None:
        if usage_amount < 0:
            flags.append("negative_usage")  # legitimate under net metering — review, not reject
        # zero usage is legitimate (vacant property, standing charges only) —
        # magnitude checks only apply to strictly positive consumption
        band = DAILY_BANDS.get(usage_unit or "")
        if band and days and days > 0 and usage_amount > 0:
            per_day = float(usage_amount) / days
            low, high = band
            if per_day < low or per_day > high:
                flags.append("usage_magnitude_suspect")
    return flags

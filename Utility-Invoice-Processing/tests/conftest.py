"""Shared test fixtures and factories."""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from invoice_extractor.ingest import IngestedDoc  # noqa: E402
from invoice_extractor.providers.base import ProviderResult  # noqa: E402
from invoice_extractor.schema import (  # noqa: E402
    CommodityReading,
    DocumentType,
    Extracted,
    FieldStatus,
    InvoiceExtraction,
    ReadType,
    UsageSource,
    UtilityType,
)

SAMPLE_TEXT = """\
ACME Power & Light Company                    Bill date: 06/15/2026
Service Address: 42 Test Lane, Springfield IL
Billing period: 05/12/2026 to 06/11/2026
Total electricity you used: 458 kWh
Total amount due: $92.15
"""


def make_extracted(value, quote, status=FieldStatus.CONFIDENT) -> Extracted:
    return Extracted(value=value, source_quote=quote, status=status)


def make_reading(**overrides) -> CommodityReading:
    defaults = dict(
        utility_type=UtilityType.ELECTRICITY,
        usage_quote="Total electricity you used: 458 kWh",
        usage_amount_raw="458",
        usage_unit_raw="kWh",
        usage_source=UsageSource.STATED_TOTAL,
        usage_status=FieldStatus.CONFIDENT,
        read_type=ReadType.UNKNOWN,
        meter_id=None,
        period_quote="Billing period: 05/12/2026 to 06/11/2026",
        billing_period_start="2026-05-12",
        billing_period_end="2026-06-11",
        period_status=FieldStatus.CONFIDENT,
    )
    defaults.update(overrides)
    return CommodityReading(**defaults)


def make_extraction(**overrides) -> InvoiceExtraction:
    defaults = dict(
        document_type=DocumentType.CONSUMPTION_INVOICE,
        language="en",
        currency="USD",
        vendor_name=make_extracted("ACME Power & Light Company", "ACME Power & Light Company"),
        invoice_date=make_extracted("2026-06-15", "Bill date: 06/15/2026"),
        service_address=make_extracted(
            "42 Test Lane, Springfield IL", "Service Address: 42 Test Lane, Springfield IL"
        ),
        total_amount=make_extracted("92.15", "Total amount due: $92.15"),
        readings=[make_reading()],
        notes=None,
    )
    defaults.update(overrides)
    return InvoiceExtraction(**defaults)


def make_doc(text: str = SAMPLE_TEXT, name: str = "acme-test.pdf") -> IngestedDoc:
    return IngestedDoc(path=Path(name), text=text, n_pages=1)


def make_result(extraction: InvoiceExtraction, mode: str = "text") -> ProviderResult:
    return ProviderResult(
        extraction=extraction,
        provider="test",
        model="test-model",
        mode=mode,  # type: ignore[arg-type]
        input_tokens=1000,
        output_tokens=200,
        latency_s=0.1,
    )

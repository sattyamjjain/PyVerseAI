"""Extraction schema — the single contract shared by both LLM providers.

This Pydantic model's JSON schema is enforced server-side (Anthropic structured
outputs / OpenAI strict json_schema), and the field descriptions below are the
highest-leverage part of the prompt: both providers see them verbatim.

Design constraints (research-backed):
- Shallow nesting and few fields: wide/deep schemas measurably degrade accuracy.
- Every leaf is nullable and REQUIRED (OpenAI strict mode forbids defaults):
  the model must actively decide "not on this document" instead of skipping.
- The model returns numbers/dates AS PRINTED plus a verbatim quote; all
  normalization is deterministic Python, so it is unit-testable and free.
- source_quote fields let code verify the value appears in the document —
  a substring check that doubles as a hallucination filter.
"""

from __future__ import annotations

from enum import StrEnum

from pydantic import BaseModel, Field


class FieldStatus(StrEnum):
    CONFIDENT = "confident"  # explicit label on the bill, unambiguous
    AMBIGUOUS = "ambiguous"  # several candidates, best one chosen
    INFERRED = "inferred"  # derived from context (e.g. year from bill date)
    NOT_FOUND = "not_found"  # genuinely absent -> value must be null


class UtilityType(StrEnum):
    ELECTRICITY = "electricity"
    GAS = "gas"
    WATER = "water"
    SEWER = "sewer"
    OTHER = "other"


class ReadType(StrEnum):
    ACTUAL = "actual"
    ESTIMATED = "estimated"
    CUSTOMER_READ = "customer_read"
    COMPUTED = "computed"
    MIXED = "mixed"
    UNKNOWN = "unknown"


class UsageSource(StrEnum):
    STATED_TOTAL = "stated_total"  # the bill prints a total for this commodity
    SUMMED_COMPONENTS = "summed_components"  # no printed total; complete disjoint register split
    READ_DIFFERENCE = "read_difference"  # only current - previous meter reads
    NOT_FOUND = "not_found"


class DocumentType(StrEnum):
    CONSUMPTION_INVOICE = "consumption_invoice"
    INSTALLMENT_NOTICE = "installment_notice"  # Abschlag / budget billing: no real usage
    CREDIT_NOTE = "credit_note"
    OTHER = "other"


class Extracted(BaseModel):
    """One document-level field with its evidence."""

    source_quote: str | None = Field(
        description=(
            "Verbatim snippet (<=200 chars) copied EXACTLY from the document, including "
            "original separators, accents and label text, proving where the value comes "
            "from. null only when the field is not on the document."
        )
    )
    value: str | None = Field(
        description="The extracted value, or null if absent. Never guess: an empty cell "
        "is recoverable downstream, an invented value silently corrupts the dataset."
    )
    status: FieldStatus


class CommodityReading(BaseModel):
    """Usage for ONE commodity on the invoice. A combined bill (e.g. gas + electricity)
    gets one entry per commodity. The SAME energy restated under tariff components,
    time-of-use splits or capacity charges is still ONE reading — never sum lines."""

    utility_type: UtilityType
    usage_quote: str | None = Field(
        description="Verbatim line containing the usage figure, e.g. 'Total Gas you used "
        "in therms: 83.9' or 'Gesamtverbrauch 7.140 kWh'. null if no usage is stated."
    )
    usage_amount_raw: str | None = Field(
        description=(
            "The consumption NUMBER exactly as printed — keep commas, periods, spaces and "
            "apostrophes ('48 469', '2.157,5', '222,45'); strip the unit. Prefer the "
            "bill's own stated total. NEVER convert units, NEVER use monetary amounts, "
            "contracted power (kW/kVA), demand, or installment/Abschlag amounts. Do not "
            "sum line items — with ONE exception: if no total is printed anywhere and the "
            "bill shows a complete disjoint register split (e.g. peak + off-peak covering "
            "the whole period), you may report their sum with usage_source="
            "summed_components and status inferred. Never include tariff-component or "
            "capacity lines that restate the same energy."
        )
    )
    usage_unit_raw: str | None = Field(
        description="Unit exactly as printed NEXT TO that same number: 'kWh', 'therms', "
        "'m³', 'CCF', 'units', 'gallons'. Copy from the same line, never infer from the "
        "commodity type."
    )
    usage_source: UsageSource
    usage_status: FieldStatus = Field(
        description="Confidence in the usage figure itself: confident only when one "
        "clearly-labelled total exists for this commodity; ambiguous when several "
        "candidates compete (multiple accounts, metered vs billed, m³ vs kWh)."
    )
    read_type: ReadType = Field(
        description="How the meter was read, if the bill says (e.g. 'estimated', a "
        "reading suffixed E, 'Kundenablesung'). unknown when not stated."
    )
    meter_id: str | None = Field(
        description="Meter / counter number for this commodity if printed, else null."
    )
    period_quote: str | None = Field(
        description="Verbatim snippet showing the billing period for this commodity, "
        "e.g. 'Bill Period: 01/05/2026 to 02/02/2026' or 'del 08/05/2018 a 10/06/2018'."
    )
    billing_period_start: str | None = Field(
        description=(
            "Period start as ISO YYYY-MM-DD. Interpret day/month order from the "
            "document's locale (language, currency, address country): European bills are "
            "almost always DD/MM/YYYY or DD.MM.YYYY, US bills MM/DD/YYYY. If the year is "
            "missing, infer it from the invoice date and set status to inferred. If the "
            "period appears only as meter-read dates, use those and set status inferred. "
            "Placeholder dates like 00/00/0000 are null + not_found."
        )
    )
    billing_period_end: str | None = Field(
        description="Period end as ISO YYYY-MM-DD, same rules as billing_period_start."
    )
    period_status: FieldStatus


class InvoiceExtraction(BaseModel):
    """Structured contents of one utility invoice."""

    document_type: DocumentType = Field(
        description="consumption_invoice for a normal bill. installment_notice for "
        "budget-billing/Abschlag/mensualisation documents (fixed amount, no real usage "
        "— do NOT report a forecast annual consumption as usage). credit_note for "
        "Gutschrift/avoir/nota de abono."
    )
    language: str | None = Field(
        description="Dominant language of the document as ISO 639-1 ('en', 'es', 'fr', "
        "'de'). For bilingual documents, the language the billing data is labelled in."
    )
    currency: str | None = Field(
        description="ISO 4217 currency of the amounts ('USD', 'EUR'), from symbols or "
        "labels; null if none appears."
    )
    vendor_name: Extracted = Field(
        description="The utility company ISSUING the invoice (not the customer, not the "
        "grid operator, not a price-comparison brand). Keep official suffixes as printed."
    )
    invoice_date: Extracted = Field(
        description="The date the invoice/statement itself was issued (Rechnungsdatum, "
        "fecha de factura, date de facture, 'Bill date') as ISO YYYY-MM-DD in value. NOT "
        "the due date, NOT a meter-read date, NOT the 'next bill' date."
    )
    service_address: Extracted = Field(
        description=(
            "The SUPPLY/service address where the utility is delivered (Service Address, "
            "dirección de suministro, Verbrauchsstelle, espace/point de livraison) as one "
            "line. This is often NOT the mailing or payment address — if only a mailing "
            "address exists, return null with status not_found rather than substituting."
        )
    )
    total_amount: Extracted = Field(
        description="Total amount due for THIS invoice as printed (number only in value, "
        "as printed, e.g. '90,15'). Careful: 'total due' may include a previous unpaid "
        "balance — prefer the amount labelled as this period's total; note ambiguity in "
        "status."
    )
    readings: list[CommodityReading] = Field(
        description="One entry per commodity billed with usage on this invoice (a "
        "combined electric+gas bill has two). Empty list if the document bills no "
        "commodity at all."
    )
    notes: str | None = Field(
        description="One or two short sentences on anything ambiguous or unusual worth "
        "a human reviewer's attention; null if nothing."
    )


# ---------------------------------------------------------------------------
# Internal (not LLM-facing): one flattened CSV row per (invoice x commodity).

CSV_COLUMNS: list[str] = [
    # the assessment's required fields, in its order
    "vendor_name",
    "invoice_date",
    "service_address",
    "utility_type",
    "usage_amount",
    "usage_unit",
    "billing_period_start",
    "billing_period_end",
    # justified additions (see DECISIONS.md)
    "currency",
    "total_amount",
    "meter_id",
    "read_type",
    "usage_source",
    "document_type",
    "language",
    "extraction_status",
    "validation_flags",
    "source_file",
]


class InvoiceRow(BaseModel):
    """One normalized, validated CSV row."""

    vendor_name: str | None = None
    invoice_date: str | None = None  # ISO
    service_address: str | None = None
    utility_type: str | None = None
    usage_amount: str | None = None  # canonical decimal string, e.g. "48469" / "222.45"
    usage_unit: str | None = None
    billing_period_start: str | None = None
    billing_period_end: str | None = None
    currency: str | None = None
    total_amount: str | None = None
    meter_id: str | None = None
    read_type: str | None = None
    usage_source: str | None = None
    document_type: str | None = None
    language: str | None = None
    extraction_status: str = "ok"  # ok | review | failed
    validation_flags: str = ""  # ';'-joined sorted flag codes
    source_file: str = ""

    def as_csv_dict(self) -> dict[str, str]:
        data = self.model_dump()
        return {col: ("" if data[col] is None else str(data[col])) for col in CSV_COLUMNS}

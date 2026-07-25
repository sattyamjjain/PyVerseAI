"""Pipeline orchestration: ingest -> extract -> normalize -> validate -> rows.

The LLM does semantics (find the fields, quote the evidence); deterministic
code does everything checkable (parse numbers/dates, verify quotes, apply
business rules). Every document yields at least one CSV row — failures are
rows too, with extraction_status=failed, so the output always accounts for
every input.
"""

from __future__ import annotations

import json
import time
from dataclasses import dataclass, field
from datetime import UTC, datetime
from pathlib import Path

from . import config
from .ingest import IngestedDoc, extract_text
from .normalize import (
    crosscheck_date,
    fold_text,
    normalize_unit,
    parse_iso_date,
    parse_localized_number,
)
from .providers import ExtractionProvider, ProviderError, ProviderResult
from .schema import (
    DocumentType,
    Extracted,
    FieldStatus,
    InvoiceExtraction,
    InvoiceRow,
)
from .validate import reading_flags, verify_quote

# Below this many characters the "text layer" is not a bill, it's noise.
MIN_TEXT_CHARS = 200

# Statuses that route a row to human review when they appear on a core field.
_REVIEW_STATUSES = {FieldStatus.AMBIGUOUS, FieldStatus.INFERRED}


@dataclass
class FileOutcome:
    source_file: str
    rows: list[InvoiceRow]
    detail: dict
    result: ProviderResult | None = None
    error: str | None = None


@dataclass
class RunSummary:
    provider: str
    model: str
    mock: bool
    outcomes: list[FileOutcome] = field(default_factory=list)
    wall_s: float = 0.0

    @property
    def rows(self) -> list[InvoiceRow]:
        return [row for outcome in self.outcomes for row in outcome.rows]


def _has_usage(extraction: InvoiceExtraction) -> bool:
    return any(r.usage_amount_raw for r in extraction.readings)


def process_document(path: Path, provider: ExtractionProvider, vision: str = "auto") -> FileOutcome:
    """Extract one document; auto-falls back to vision when the text layer
    exists but carries no figures (annotated sample bills do exactly this)."""
    doc = extract_text(path)
    live = not provider.name.startswith("mock")
    result: ProviderResult | None = None
    error: str | None = None

    try:
        if doc.n_chars >= MIN_TEXT_CHARS:
            result = provider.extract_text_mode(doc.text, path.name)
            if (
                live
                and vision == "auto"
                and provider.supports_vision
                and result.mode == "text"
                and path.suffix.lower() == ".pdf"
                and not _has_usage(result.extraction)
            ):
                retry = provider.extract_vision_mode(path.read_bytes(), path.name)
                if _has_usage(retry.extraction):
                    # keep paying for both calls honest: merge token counts
                    retry.input_tokens += result.input_tokens
                    retry.output_tokens += result.output_tokens
                    result = retry
        elif vision != "off" and provider.supports_vision and path.suffix.lower() == ".pdf":
            result = provider.extract_vision_mode(path.read_bytes(), path.name)
        else:
            error = "no_text_layer (rerun with a vision-capable provider or --vision auto)"
    except ProviderError as exc:
        error = str(exc)

    if result is None:
        row = InvoiceRow(
            extraction_status="failed",
            validation_flags="extraction_error",
            source_file=path.name,
        )
        detail = {"source_file": path.name, "error": error}
        return FileOutcome(path.name, [row], detail, None, error)

    rows, detail = postprocess(result, doc)
    return FileOutcome(path.name, rows, detail, result, None)


def postprocess(result: ProviderResult, doc: IngestedDoc) -> tuple[list[InvoiceRow], dict]:
    """Deterministic half of the pipeline. Pure given (result, doc) — this is
    what fixture-replay tests exercise end to end."""
    ex = result.extraction
    lang = (ex.language or "").lower() or None
    folded_doc = fold_text(doc.text)
    quotes_verifiable = result.mode == "text"
    shared_flags: list[str] = []
    field_checks: dict[str, dict] = {}

    def check(name: str, item: Extracted) -> str | None:
        """Verify evidence for one document-level field; returns its value."""
        verified = quotes_verifiable and verify_quote(item.source_quote, folded_doc)
        if item.value is not None and quotes_verifiable and not verified:
            shared_flags.append(f"quote_unverified_{name}")
        field_checks[name] = {
            "value": item.value,
            "status": item.status.value,
            "source_quote": item.source_quote,
            "quote_verified": verified if quotes_verifiable else None,
        }
        return item.value

    vendor = check("vendor_name", ex.vendor_name)
    invoice_date_raw = check("invoice_date", ex.invoice_date)
    address = check("service_address", ex.service_address)
    total_raw = check("total_amount", ex.total_amount)

    invoice_dt = parse_iso_date(invoice_date_raw)
    if invoice_date_raw and invoice_dt is None:
        shared_flags.append("invoice_date_not_iso")
    if flag := crosscheck_date(invoice_date_raw, ex.invoice_date.source_quote, lang):
        shared_flags.append(f"{flag}_invoice_date")

    total_amount = parse_localized_number(total_raw, lang)
    if total_raw is not None and total_amount is None:
        shared_flags.append("total_amount_unparseable")

    if not quotes_verifiable:
        shared_flags.append("vision_mode_quotes_unverifiable")

    doc_statuses = [ex.vendor_name.status, ex.invoice_date.status]

    rows: list[InvoiceRow] = []
    reading_details: list[dict] = []
    for reading in ex.readings:
        flags = list(shared_flags)
        statuses = list(doc_statuses) + [reading.usage_status, reading.period_status]

        usage = parse_localized_number(reading.usage_amount_raw, lang)
        if reading.usage_amount_raw is not None and usage is None:
            flags.append("usage_unparseable")
        unit, unit_flag = normalize_unit(reading.usage_unit_raw)
        if unit_flag:
            flags.append(unit_flag)

        start = parse_iso_date(reading.billing_period_start)
        end = parse_iso_date(reading.billing_period_end)
        for bound, value in (
            ("start", reading.billing_period_start),
            ("end", reading.billing_period_end),
        ):
            if value and parse_iso_date(value) is None:
                flags.append(f"period_{bound}_not_iso")
        if flag := crosscheck_date(reading.billing_period_start, reading.period_quote, lang):
            flags.append(f"{flag}_period_start")
        if flag := crosscheck_date(reading.billing_period_end, reading.period_quote, lang):
            flags.append(f"{flag}_period_end")

        if quotes_verifiable:
            for label, quote, has_value in (
                ("usage", reading.usage_quote, usage is not None),
                ("period", reading.period_quote, start is not None or end is not None),
            ):
                if has_value and not verify_quote(quote, folded_doc):
                    flags.append(f"quote_unverified_{label}")

        flags.extend(
            reading_flags(
                usage_amount=usage,
                usage_unit=unit,
                period_start=start,
                period_end=end,
                invoice_date=invoice_dt,
            )
        )

        if ex.document_type is DocumentType.INSTALLMENT_NOTICE and usage is None:
            flags.append("installment_notice_no_usage")  # correct behaviour, informational

        core_missing = usage is None or start is None or end is None or vendor is None
        needs_review = (
            bool(flags)
            or any(s in _REVIEW_STATUSES for s in statuses)
            or (core_missing and ex.document_type is DocumentType.CONSUMPTION_INVOICE)
        )
        rows.append(
            InvoiceRow(
                vendor_name=vendor,
                invoice_date=invoice_dt.isoformat() if invoice_dt else None,
                service_address=address,
                utility_type=reading.utility_type.value,
                usage_amount=str(usage) if usage is not None else None,
                usage_unit=unit,
                billing_period_start=start.isoformat() if start else None,
                billing_period_end=end.isoformat() if end else None,
                currency=ex.currency,
                total_amount=str(total_amount) if total_amount is not None else None,
                meter_id=reading.meter_id,
                read_type=reading.read_type.value,
                usage_source=reading.usage_source.value,
                document_type=ex.document_type.value,
                language=lang,
                extraction_status="review" if needs_review else "ok",
                validation_flags=";".join(sorted(set(flags))),
                source_file=doc.path.name,
            )
        )
        reading_details.append(
            {
                "utility_type": reading.utility_type.value,
                "usage_amount_raw": reading.usage_amount_raw,
                "usage_unit_raw": reading.usage_unit_raw,
                "usage_quote": reading.usage_quote,
                "period_quote": reading.period_quote,
                "usage_status": reading.usage_status.value,
                "period_status": reading.period_status.value,
                "flags": sorted(set(flags)),
            }
        )

    if not rows:  # document billed no commodity (or model found none)
        flags = list(shared_flags) + ["no_readings"]
        nothing_found = vendor is None and invoice_dt is None
        rows.append(
            InvoiceRow(
                vendor_name=vendor,
                invoice_date=invoice_dt.isoformat() if invoice_dt else None,
                service_address=address,
                currency=ex.currency,
                total_amount=str(total_amount) if total_amount is not None else None,
                document_type=ex.document_type.value,
                language=lang,
                extraction_status="failed" if nothing_found else "review",
                validation_flags=";".join(sorted(set(flags))),
                source_file=doc.path.name,
            )
        )

    detail = {
        "source_file": doc.path.name,
        "provider": result.provider,
        "model": result.model,
        "mode": result.mode,
        "input_tokens": result.input_tokens,
        "output_tokens": result.output_tokens,
        "latency_s": round(result.latency_s, 2),
        "cost_usd": round(
            config.cost_usd(result.model, result.input_tokens, result.output_tokens), 6
        ),
        "language": lang,
        "document_type": ex.document_type.value,
        "notes": ex.notes,
        "fields": field_checks,
        "readings": reading_details,
        "n_pages": doc.n_pages,
        "n_text_chars": doc.n_chars,
    }
    return rows, detail


def write_fixture(outcome: FileOutcome) -> None:
    """Persist the raw model output so mock runs and tests can replay it."""
    if outcome.result is None:
        return
    stem = Path(outcome.source_file).stem
    config.FIXTURES_DIR.mkdir(parents=True, exist_ok=True)
    payload = {
        "source_file": outcome.source_file,
        "provider": outcome.result.provider,
        "model": outcome.result.model,
        "mode": outcome.result.mode,
        "input_tokens": outcome.result.input_tokens,
        "output_tokens": outcome.result.output_tokens,
        "latency_s": round(outcome.result.latency_s, 2),
        "extraction": json.loads(outcome.result.extraction.model_dump_json()),
    }
    path = config.FIXTURES_DIR / f"{stem}.{outcome.result.provider}.json"
    path.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def run_pipeline(
    files: list[Path],
    provider: ExtractionProvider,
    *,
    vision: str = "auto",
    record_fixtures: bool = True,
    verbose: bool = False,
) -> RunSummary:
    summary = RunSummary(
        provider=provider.name,
        model=getattr(provider, "model", provider.name),
        mock=provider.name.startswith("mock"),
    )
    t0 = time.perf_counter()
    for path in files:
        outcome = process_document(path, provider, vision=vision)
        summary.outcomes.append(outcome)
        if record_fixtures and not summary.mock:
            write_fixture(outcome)
        if verbose:
            _print_outcome(outcome)
    summary.wall_s = time.perf_counter() - t0
    return summary


def _print_outcome(outcome: FileOutcome) -> None:
    if outcome.error:
        print(f"  ✗ {outcome.source_file}: {outcome.error}")
        return
    kinds = ", ".join(r.utility_type or "?" for r in outcome.rows)
    statuses = {r.extraction_status for r in outcome.rows}
    mode = outcome.result.mode if outcome.result else "?"
    print(
        f"  ✓ {outcome.source_file} [{mode}] -> {len(outcome.rows)} row(s) "
        f"({kinds}) status={'/'.join(sorted(statuses))}"
    )


def build_run_report(summary: RunSummary, csv_path: Path) -> dict:
    input_tokens = sum(o.result.input_tokens for o in summary.outcomes if o.result)
    output_tokens = sum(o.result.output_tokens for o in summary.outcomes if o.result)
    cost = sum(
        config.cost_usd(o.result.model, o.result.input_tokens, o.result.output_tokens)
        for o in summary.outcomes
        if o.result
    )
    rows = summary.rows
    n_files = len(summary.outcomes)
    statuses = {"ok": 0, "review": 0, "failed": 0}
    for row in rows:
        statuses[row.extraction_status] = statuses.get(row.extraction_status, 0) + 1
    return {
        "generated_at": datetime.now(UTC).isoformat(timespec="seconds"),
        "provider": summary.provider,
        "model": summary.model,
        "mock": summary.mock,
        "csv": str(csv_path),
        "files": n_files,
        "rows": len(rows),
        "row_status_counts": statuses,
        "languages": sorted({row.language for row in rows if row.language}),
        "utility_types": sorted({row.utility_type for row in rows if row.utility_type}),
        "input_tokens": input_tokens,
        "output_tokens": output_tokens,
        "cost_usd": round(cost, 4),
        "cost_per_invoice_usd": round(cost / n_files, 4) if n_files else 0.0,
        "wall_s": round(summary.wall_s, 1),
        "per_file": [
            {
                "file": o.source_file,
                "mode": o.result.mode if o.result else None,
                "rows": len(o.rows),
                "statuses": sorted({r.extraction_status for r in o.rows}),
                "flags": sorted({f for r in o.rows for f in r.validation_flags.split(";") if f}),
                "cost_usd": round(
                    config.cost_usd(o.result.model, o.result.input_tokens, o.result.output_tokens),
                    6,
                )
                if o.result
                else 0.0,
                "error": o.error,
            }
            for o in summary.outcomes
        ],
    }


def write_details(summary: RunSummary, details_dir: Path) -> None:
    details_dir.mkdir(parents=True, exist_ok=True)
    for outcome in summary.outcomes:
        stem = Path(outcome.source_file).stem
        target = details_dir / f"{stem}.{summary.provider.replace(':', '_')}.json"
        target.write_text(
            json.dumps(outcome.detail, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
        )

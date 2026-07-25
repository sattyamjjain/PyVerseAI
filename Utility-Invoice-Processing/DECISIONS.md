# Decision log

Format per entry: **Decision** — why · trade-off · what I'd change with more time/scale.

1. **Plain provider SDKs, no framework (no LangChain/instructor).**
   Both providers now enforce JSON schemas server-side and retry transient failures in
   the SDK; a framework wraps those same calls in indirection a reviewer must read.
   Trade-off: I re-implement a thin provider interface (~60 lines). At scale I'd adopt
   `instructor` first — its validation-reask loop becomes useful the day I need
   semantic (not schema) retries.

2. **`claude-sonnet-5`, `effort: medium`, no sampling params.**
   Multilingual extraction quality is the axis that matters; the whole 8-bill run
   costs $0.39, so model-cost optimization here is theatre — measured, not assumed:
   the identical-prompt OpenAI comparison (98.7% vs 84.4%) is in the eval report.
   Note current Claude models return HTTP 400 for `temperature=0` — the old
   "always pin temperature" advice now *breaks* pipelines. Effort is sent only to
   models that support it (Haiku 4.5 errors on it).

3. **One CSV row per (invoice × commodity).**
   Combined bills are ~a third of this corpus (We Energies electric+gas, SFPUC
   water+sewer). One row per document would force a `utility_type=combined` fudge and
   drop real usage data. This mirrors how Arcadia/UtilityAPI model bills.
   Trade-off: consumers must group by `source_file`.

4. **LLM returns values as printed + verbatim quotes; Python normalizes.**
   Numbers (`48 469`, `2.157,5`, lakh grouping), ISO dates and unit labels are
   deterministic, unit-testable transformations — putting them in the prompt would
   make the least reliable component responsible for the most checkable work. The
   exception: date *interpretation* (DD/MM vs MM/DD) uses the LLM's whole-document
   locale context, cross-checked independently by `dateparser`.

5. **Confidence = categorical status + code-verified evidence quotes. No floats.**
   Anthropic exposes no logprobs, and self-reported numeric confidence is documented
   to collapse toward over-confidence. A quote that fails the (space-insensitive)
   substring check demotes the row to review regardless of claimed status — a
   deterministic hallucination filter that caught the only extraction error of the
   live run.

6. **Normalize unit labels; never convert values.**
   CCF→therms requires a per-utility, per-month heat factor (×1.062 on We Energies,
   ×0.974×1.058 on MidAmerican — printed on the bills themselves). Any hard-coded
   factor is silently wrong somewhere. Stopping at label normalization is a
   correctness decision, not a missing feature.

7. **Usage from stated totals; summing only for complete disjoint register splits.**
   Summing kWh lines on the Vialis bill yields ~2× actual (capacity components restate
   energy). But Iberdrola prints *no* total — only PUNTA 163 + VALLE 187 — so a narrow
   exception exists: disjoint registers may be summed, marked
   `usage_source=summed_components` + `status=inferred`, review-routed.

8. **Vision fallback (Claude PDF input) only when the text layer has no figures.**
   Native PDF input costs image+text tokens per page (~10× text-only). Auto-retry
   triggered exactly once in this corpus (EDF) and recovered the full row. OpenAI path
   ships text-only — the measured accuracy gap that causes is part of the comparison,
   not hidden.

9. **`pdfplumber` (MIT) with `layout=True`.**
   Layout-aware extraction preserves the positional meaning invoices rely on. PyMuPDF
   is AGPL-3.0 and `marker` is GPL-3.0 — genuine constraints for commercial use.
   Known cost: tightly-kerned words merge (`CurrentBillingPeriod`), which quote
   verification now tolerates by design.

10. **Reproducibility as a feature: fixtures + `--mock` + byte-identical CSV.**
    Recorded raw model responses are committed; `make run-mock` regenerates the
    committed CSV byte-for-byte and the test suite runs free and offline. `.gitattributes`
    pins the CSVs as `-text` so git cannot normalize their RFC-4180 CRLF endings.

11. **`utf-8-sig` CSV encoding.**
    Excel renders bare-UTF-8 "Québec" as "QuÃ©bec". Every other consumer ignores
    the BOM. The target user of a CSV deliverable opens it in a spreadsheet.

12. **Failures are rows, not exceptions.**
    Every input document yields ≥1 CSV row; unusable documents produce
    `extraction_status=failed` with a reason flag. The output always accounts for
    every input — an auditability property borrowed from bill-audit platforms.

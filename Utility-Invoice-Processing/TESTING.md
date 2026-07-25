# Testing approach

The evaluation criteria this project was built against name "testing and validation
thinking" as a graded axis, so this document treats measurement as a first-class
artifact: how accuracy was validated, what was deliberately stress-tested, what broke
during development (and how the harness caught it), and what I would do next.

## 1. How accuracy was validated

**Hand-labeled golden data, deterministic scoring.** I read every sample bill
*visually* (as rendered pages, not extracted text) and labeled all 7 scored fields per
commodity row in [`eval/golden_labels.yaml`](eval/golden_labels.yaml) — before looking
at any model output, so the labels couldn't be anchored by predictions. `invoice-eval`
then scores a produced CSV with type-aware matchers: `Decimal` equality for amounts
(83.9 ≡ 83.90), exact ISO for dates, alias/substring folding for vendor names,
punctuation-insensitive substring for addresses. No LLM-as-judge anywhere — for field
extraction, `==` does not hallucinate, and judging equality with a model would be
over-engineering.

**The error taxonomy is the point.** Each field judgment lands in one of:

`correct_exact` · `correct_normalized` · `missing_correct` (golden null, predicted
null — **the null was right**) · `missing_wrong` (recall failure) ·
`hallucinated` (golden null, predicted value — **the worst class**) · `wrong_value`

Separating "returned null correctly" from "returned null wrongly" from "invented a
value" is what makes the numbers actionable. `missing_correct` counts toward accuracy
deliberately: not rewarding correct nulls incentivises guessing. The golden set was
built to give this taxonomy teeth — it contains real nulls (two bills genuinely print
no invoice date; one prints no service address) so hallucination is *measurable*, not
hypothetical.

**Results** ([full report](outputs/eval_report.md)): claude-sonnet-5 scored **98.7%**
over 77 field judgments (56 exact + 17 normalized + 3 correct-nulls), with 100% on
`usage_amount`, `usage_unit` and both period dates, and per-language accuracy of
100/100/100/98% (es/fr/de/en). The single error: Central Hudson's *own HQ address*
extracted as the service address — the classic mailing-vs-service trap, and notably
**the pipeline flagged that exact row for review** (`quote_unverified_service_address`,
status `ambiguous`), so the confidence loop caught the one mistake the extractor made.
gpt-5.6-terra on the identical prompt/schema: 84.4%, mostly because it has no PDF-vision
path so the image-only EDF bill contributes misses — a measured argument for the
vision fallback rather than an asserted one.

## 2. Edge cases considered

Legend: ✅ handled · 🔶 detected & flagged for review · ⬜ documented out-of-scope.

| Edge case | Status | Evidence |
|---|---|---|
| European decimal comma / dot-thousands (`2.157,5`) | ✅ | de bill parses 859, not 0.859 or 859 000; unit tests carry the 1000× worked failures |
| French space-as-thousands (`48 469`, NBSP/narrow variants) | ✅ | Vialis → 48469; byte-level variants unit-tested |
| Indian lakh grouping (`5,67,780.22`) | ✅ | unit test (period-decimal branch strips all commas) |
| DD/MM vs MM/DD ambiguity | ✅/🔶 | locale-seeded cross-check; disagreement flags `date_crosscheck_failed_*` instead of silently choosing |
| Combined multi-commodity bills | ✅ | We Energies → electricity + gas rows; SFPUC → water + sewer rows |
| Billing period only derivable from meter-read dates | 🔶 | MidAmerican: correct dates, `status=inferred` → review |
| Year-less period ("May 2 - Jun 3") | 🔶 | PPL: year inferred from bill context → correct 2024 dates, review-routed |
| No printed usage total, only disjoint TOU registers | 🔶 | Iberdrola: 163+187 summed under the narrow `summed_components` rule, marked inferred |
| Same energy restated under tariff components | ✅ | Vialis: stated total 48 469 chosen; components not summed |
| kW (demand/contracted power) vs kWh | ✅ | `Potencia contratada 3,45 kW` never lands in usage; demand units flag if they ever do |
| On-bill unit conversions (CCF↔therms, m³↔kWh) | ✅ | unit taken from the same line as the chosen number; values never converted |
| Placeholder values (`00/00/0000`, `000.0000`, `Month 00, 0000`) | ✅ | CUB explainer: all nulls; the "800 kWh" rate-tier bait was not taken |
| Missing invoice date / service address (genuinely absent) | ✅ | SWM + Central Hudson dates → null, no invention |
| Estimated vs actual meter reads | ✅ | `read_type` enum (not a boolean), `unknown` default; mixed reads captured in notes |
| Zero usage ≠ null usage | ✅ | validator treats 0 as legitimate (vacant property); unit-tested |
| Negative usage (net metering, credit notes) | 🔶 | flagged `negative_usage`, never rejected |
| Image-only PDF (no figures in text layer) | ✅ | EDF: auto vision fallback; quotes marked unverifiable in that mode |
| Internally contradictory period (2024→2021) | 🔶 | lapalma teaching deck: refused extraction (`failed` row) rather than fabricating |
| Vendor's own address vs customer service address | 🔶 | the one live miss; flagged by quote verification (see §4) |
| Multi-page bills, summary vs detail restatement | ✅ | Central Hudson restates 458 kWh 3× across delivery/supply/ESCO — one row emitted |
| Scanned/photographed paper bills (true OCR) | ⬜ | out of scope per brief; vision path covers image-PDFs but is untested on photos |
| Multi-invoice concatenated PDFs | ⬜ | would need a document splitter stage |
| Deregulated split billing (two invoices, one meter) | ⬜ | schema carries `meter_id` to make the join possible downstream |

## 3. Automated tests

113 tests, three tiers, **`pytest` passes with no API key and no network** — a
reviewer can clone and verify before reading any code:

1. **Pure-function tests** (the majority): number/date/unit normalizers and business
   validators, parametrized with every worked failure case above. This is the payoff
   of the LLM/code boundary — the code that breaks on multilingual bills is plain
   Python under exhaustive test.
2. **Fixture-replay tests**: the committed raw model responses run through the full
   downstream pipeline and must reproduce the committed `outputs/invoices.csv`
   **byte-for-byte** (a `.gitattributes` entry keeps git from normalizing the CSV's
   RFC-4180 line endings, which would otherwise break this on fresh clones — found by
   testing the clone path). Synthetic-extraction tests also drive the hallucination
   filter directly: a fabricated quote must produce `quote_unverified_*` + review.
3. **Live smoke tests** (`pytest -m live`, opt-in): one real bill end-to-end per
   provider, asserting field-level expectations.

The eval harness itself is under test (taxonomy semantics, alias matching, golden-file
completeness), and `invoice-eval --min-accuracy N` exists as a regression gate for CI.

## 4. What broke during development — and what caught it

Narrating these beats a clean table, because each one proves a harness component earns
its place:

- **dateparser's segmentation merged date ranges** (`"del 08/05/2018 a 10/06/2018"`
  under `languages=["es"]` → one garbage date, year 0008). Caught by the cross-check
  unit tests; fixed by regex-tokenizing dates and parsing each token individually.
- **pdfplumber's layout mode merges tightly-kerned words** (`CurrentBillingPeriod
  May25,2021`), and models sometimes strip spaces when quoting. Both directions broke
  naive quote verification on the very first live invoice. Fix: space-insensitive
  verification (a fabricated quote still can't match the de-spaced document) plus
  seam-normalized month-name date tokens.
- **The model returned the utility's own HQ as the service address** on Central
  Hudson (whose real service address is redacted). A schema-description strengthening
  reduced but did not eliminate it; the residual case is *flagged for review* by quote
  verification — which is the designed behavior for extraction errors that survive
  prompting: fail visibly, not silently.
- **git's CRLF normalization** would have silently broken byte-identical replay on
  fresh clones (see tier 2).

## 5. How I'd improve testing with more time

Ordered by value, each tied to something observed in this build:

1. **Scale the golden set toward saturation.** 11 labeled rows is far short of the
   ~100-trace error-analysis standard; I'd add bills until ~20 consecutive new samples
   produce no new failure category, prioritizing the gaps this corpus exposed:
   sample bills are systematically *cleaner* than real bills (published specimens have
   text layers and redacted-but-tidy layouts), plus Abschlag/budget-billing documents,
   net-metering statements with negative net usage, and non-Latin scripts.
2. **Confidence calibration measurement.** The categorical statuses route rows to
   review; with more labeled data I'd measure how often `confident`+verified is
   actually correct vs `ambiguous`/`inferred` (on this run: the only wrong field sat
   in a review-routed row — encouraging, n=1) and set the review threshold from that
   curve instead of by construction.
3. **Second annotator + adjudication** on the golden labels — several labels are
   judgment calls (documented in §6) and single-annotator bias is currently unmeasured.
4. **Model-swap matrix as a standing eval**: same golden set across Haiku/Sonnet and
   GPT tiers per prompt change, so cost/accuracy trade-offs stay measured over time
   (the harness already supports `--compare`).
5. **Synthetic bill generator** for locales with no publishable samples: template-render
   invoices with known ground truth → unlimited labeled data for the normalizer paths,
   without shipping anyone's real bill.
6. **Property-based tests** (hypothesis) for `parse_localized_number` — the
   hand-parametrized cases cover known formats; fuzzing would cover the unknown ones.

## 6. Golden-label judgment calls

Documented so the accuracy numbers are auditable rather than convenient:

- **We Energies gas = 83.9 therms** (billing headline), not 79 CCF (metered volume) —
  both are printed; charges are computed per therm. A CCF answer scores `wrong_value`.
- **SFPUC water = 6.40 "units"** as printed (1 unit = 1 CCF = 748 gal); sewer = 5.76
  discharge units (the bill's own computed 90% flow factor). The 4,787-gallon
  restatement is a defensible alternate that would score wrong under these labels.
- **Iberdrola = 350 kWh** via the disjoint-register exception (the bill prints no
  total). A strict-null answer is defensible; I chose the label that matches what a
  utility-data platform must deliver, and required the pipeline to mark it inferred.
- **CUB explainer is not numerically scored**: an all-placeholder template makes "one
  null electricity row" and "no rows" equally correct shapes. Its behavioral test —
  don't take the 800 kWh tier boundary as usage, don't parse `00/00/0000` into dates —
  passed by inspection and is pinned by the committed fixture.

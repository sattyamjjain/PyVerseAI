# Solution — Product Matching System

Matching German construction-tender line items (*Leistungsverzeichnis* positions) to a
Duravit sanitary-product catalog. Three methods of increasing capability, one shared
evaluation framework, every experiment kept per the challenge rules.

## Quickstart

```bash
python3 -m venv .venv && .venv/bin/pip install -r requirements.txt   # Python 3.9+ (developed on 3.14)
cp .env.example .env        # paste your OPENAI_API_KEY (optional, see below)

.venv/bin/python scripts/demo.py        # match 3 example tender lines, ~10 s
.venv/bin/python -m pytest tests/ -q    # contract tests, no API needed
.venv/bin/python scripts/run_eval.py    # full evaluation -> experiments/results/
.venv/bin/python scripts/run_eval.py --no-llm --no-dense   # fully offline variant
```

Without a key everything still runs: the dense ranker is skipped and Method 3 degrades to
the deterministic cascade. The shipped `.cache/rerank.sqlite` replays every Method 3
LLM answer from disk (with `RERANK_MODEL` pinned as in `.env.example`), so `run_eval.py`
reproduces the table below without spending anything; a first run from an empty cache
costs roughly $2–3 on a mini-tier model. Offline partial runs write `*_partial.json` so
they never clobber the canonical artifacts.

## TL;DR results

All numbers regenerate into `experiments/results/results.json`
(models: `text-embedding-3-large` @1024 dims, `gpt-5.4-mini`; precedents leave-one-out).

| Method | Full set (LOO precedents) | Unseen split* | API cost | Latency (1k rows) |
|---|---|---|---|---|
| 1 — Deterministic cascade (extraction → TF-IDF) | 0.409 | 0.374 | $0 | ~0.4 s |
| 2 — Hybrid retrieval (TF-IDF + BM25 + embeddings, RRF) | 0.295 | 0.273 | <$0.10 (cached) | ~5 s |
| 3 — Full pipeline (extraction → retrieval → LLM selection) | **0.524** | **0.490** | ~$1.5 (cached) | ~2 min uncached |

*Unseen split = duplicate-aware 80/20 group split (n=198, so ±~0.07 at 95% confidence);
precedent index sees only train rows. Method 2 is deliberately extraction-free: it is pure
retrieval top-1, so it isolates what the rankers contribute and scores below Method 1 by
design; Method 3 combines both. A trivial majority-vote-per-identical-text oracle caps this
dataset at 0.896 (see label noise below), and retrieval puts the target in the top-40
candidate list for 76.9% of rows — Method 3 converts about two thirds of what retrieval
makes reachable.

## How the headline number was almost wrong (and how we caught it)

Our first full-set number for Method 3 was **0.678**. It was inflated: the pipeline shows
the LLM the 3 most similar *historical* requirements with their chosen products as
evidence, and when evaluating on the same 1,000 labeled rows that feed that index, every
row retrieves **itself** as its top precedent (self-precedent rate: 100%), with the gold
label visible in the prompt for 99.5% of rows. Concretely: a baseline that just **copies
the nearest precedent's label scores 0.894** on that metric — *above* the pipeline. The
metric was measuring memorization, not matching.

The fix is leave-one-out discipline: precedents with text identical to the query are
excluded from the prompt (`exclude_identical_precedents=True`, the default). Post-fix,
the full-set and unseen-split numbers converge (0.524 vs 0.490) — evidence the leak is
gone. The memorization baseline is now computed and printed by `run_eval.py` on every run
(`precedent_memorization_baseline` in `results.json`: copy-top-1 falls from 0.894 to
0.226 under LOO) so the full-set column can never again be read as generalization.

Two design decisions changed when re-measured honestly:

- **Precedent value**: the leaked ablation said precedents were worth +10.5 pts. The
  honest LOO ablation says **+1.5 pts** (0.540 vs 0.525 on a 200-row sample) — real but
  modest, consistent with the honest signal strength (a train-only nearest precedent
  carries the right label for only 22.6% of rows).
- **Candidate-list size**: the leaked sweep favored k=40 by +6 pts. The honest 200-row
  sweep is flat (k∈{10,20,40}: 0.535–0.540, CI ±0.07) — but the full-run comparison at
  n=1000 gives **k=40: 0.524 vs k=20: 0.507**, and retrieval recall@40 (0.769) is well
  above recall@20 (0.684), so k=40 ships. Both sweeps are preserved in
  `experiments/results/llm_ablation.json`.

Interesting side effect: Method 3 *disagrees* with its own (89.4%-correct, self-matching)
top precedent on a third of rows — under the leaked regime it was actively discarding the
handed answer and reasoning from the catalog. Good instinct, wrong metric.

## What the data says (see `experiments/01_eda.py`)

- 2,180 products, 1,000 labeled requirements, only **318 unique targets**; top target
  appears 38×, 158 targets appear exactly once.
- **Duplication is heavy**: 319 rows sit in 138 exact-duplicate groups (after whitespace
  normalization; largest group has 5 members) → naive random splits leak; all held-out
  evaluation here is group-split by normalized text.
- **Label noise is real and quantifiable**: 83 of those duplicate groups carry
  *conflicting labels* — identical text mapping to different products — affecting 197
  rows. A majority-vote oracle on identical text therefore caps at **0.896**. This is the
  honest ceiling of the dataset, not a hand-wavy "labels are noisy".
- **27.2% of rows contain a catalog article number** in the text ("#2527090000",
  "Bestellnummer: 0302490000", alphanumeric SKUs like "C11020001010"). The first cited
  id is the answer 82.7% of the time; the answer is among the cited ids 86.0% of the
  time. Highest-precision signal available — but not infallible: sometimes the cited
  number is one component of a larger set that was actually ordered.
- Tender idioms matter: "Fabrikat/Typ: Duravit / Starck 3", "oder gleichwertig" (the
  named product is still the anchor), dimension strings ("600 x 460") in 514 rows.

## The three methods

```
requirement text
   │
   ├─ 1. article number(s) in text?  (regex + catalog validation)
   │       exactly one  → short-circuit: answer            [25.5% of rows]
   │       several      → force-include as candidates
   │
   ├─ 2. hybrid retrieval → top-40 candidates
   │       TF-IDF word(1-2) + char_wb(3-5)  ┐
   │       BM25                             ├─ Reciprocal Rank Fusion
   │       OpenAI embeddings (1024d)        ┘
   │       + top-3 similar historical requirements (leave-one-out)
   │
   └─ 3. gpt-5.4-mini selects ONE candidate (Structured Outputs)
           answer must be in the candidate list, else fallback
           to retrieval top-1                              [3.6% of LLM rows]
```

### Method 1 — Deterministic cascade (`predict_product_id_deterministic`)
Regex-extract alphanumeric tokens (7+ chars) and keep those that exist in the catalog;
exactly one → predict it; several → pick the one whose product best matches the text by
TF-IDF; none → TF-IDF top-1, or the most common historical product when the text has no
lexical signal at all. **Why it exists:** zero-cost, fully explainable, no external
dependency, and it captures the strongest single signal. This is the floor any fancier
method must beat, and the production-safe fallback when APIs are down.
Development history: `experiments/02_pure_python_baselines.py` (written dependency-free
before any ML; its 1-NN-over-history baseline is also where the leave-one-out discipline
first appears). Two measured improvements over the first version (+1.2 pts): alphanumeric
SKU extraction (the digits-only regex missed ids like `45620900A1` even when quoted
verbatim) and TF-IDF ranking among multiple cited ids instead of blindly taking the first.

### Method 2 — Hybrid retrieval (`predict_product_id_hybrid`)
Three rankers over an enriched product document (name + description + category):
- TF-IDF **word(1–2)** and **char_wb(3–5)** — char n-grams handle German compounds
  ("Tiefspülklosett" ≈ "Tiefspül-WC") and partial article numbers,
- **BM25** over normalized tokens — strong on rare exact terms,
- **OpenAI `text-embedding-3-large`** (1024 Matryoshka dims, disk-cached) — paraphrase
  and cross-wording semantics,
fused with **Reciprocal Rank Fusion** (k=60), which needs no score calibration.
Per-ranker recall@50 (`experiments/03_retrieval_ablation.py`): char/word TF-IDF 0.784,
dense embeddings 0.736, BM25 0.605 — **fusion 0.804**, beating every individual ranker:
sparse and dense fail on different rows.

### Method 3 — Full pipeline (`predict_product_id`, the deliverable)
The mental model: **retrieval provides recall, the LLM provides precision.** The LLM
selects one candidate under domain rules (series/Fabrikat lines, seat ≠ bowl, mounting,
dimensions, Rimless, color/finish, "oder gleichwertig" anchoring) with three safety
properties: it can only answer from the candidate list (out-of-list answers — 27 of 745
LLM rows, 3.6% — fall back to retrieval top-1), responses are schema-enforced via
Structured Outputs, and every call is disk-cached for reproducibility. Precedents are
included leave-one-out, as evidence of selection behavior rather than as answers.

## Where the remaining errors live

Per-category accuracy, full set, Method 3 (n = labeled rows; full names as in the data):
Wannen und Zubehör 0.83 (n=23), Armaturen 0.79 (n=14), Keramik 0.58 (n=646), WC-Sitze
0.41 (n=198), Badzubehör & Accessoires 0.40 (n=70), W&W Zubehör 0.16 (n=45). The three
categories at 1.00 have n≤2; treat everything under n=50 as directional.

Three real failure cases from `experiments/results/predictions.csv`:

1. **Variant under-specification** — "Urinale für UP Steuerungen": gold is the ME by
   Starck urinal *für Netz* (mains-powered control, `2809310093`), predicted the same
   urinal *für Batterie* (`2809310000`). The tender text never says which power variant.
2. **Assembly vs component** — "Badewanneanlage 75 x 170 x 48 cm": the text cites the
   bathtub's own Bestellnummer and the model picks the tub; the historical line item
   actually bought the *leg frame* (`790100000000000`) for that tub.
3. **Text describes X, history bought Y** — "Elektronik-Urinal": the text specifies the
   ceramic urinal; the historically selected product is the concealed *suction siphon*
   accessory (`0051120000`). The quote was split across line items in a way the text
   alone cannot reveal.

All three are variants of the same root cause: the label is "what was put on the quote",
which is not always derivable from the requirement text — the 0.896 oracle ceiling made
quantitative. In production this argues for a ranked top-3 suggestion UI with confidence
rather than a forced top-1 (the reranker already returns confidence + reasoning).

## Evaluation methodology (`src/evaluation_ext.py`, `scripts/run_eval.py`)

- **Challenge metric** (`evaluate_product_prediction` on the full labeled set) — reported
  because the challenge defines it, always alongside the **memorization baseline** that
  bounds what lookup alone achieves on it.
- **Duplicate-aware unseen split**: 80/20 grouped by normalized text (verified: zero
  test texts appear in train), precedent index rebuilt from train only. Across 5 seeds
  the offline methods vary with sd ≈ 0.03 and seed 42 sits at the pessimistic end, so
  the reported numbers are conservative.
- **Top-k retrieval recall** incl. the shipped k=40 — the reranker's ceiling.
- **Per-stage diagnostics**: extraction coverage/precision, short-circuit and fallback
  counts, per-category accuracy — all persisted in `results.json`, and every prediction
  is dumped to `predictions.csv` for error analysis.
- Contract tests in `tests/` (signature, ordering, empty/NaN inputs, alphanumeric SKUs,
  small catalogs, determinism) run without any API key.

## Approaches considered but not implemented (by design, per the brief)

- **Fine-tuned bi-/cross-encoder**: 1,000 labels across 318 classes with 158 singletons
  is too thin to fine-tune without memorizing; attractive at ~10k+ labels.
- **Structured attribute extraction**: parse both sides into a schema (type, series,
  dimensions, mounting, color, features) and match structurally — the most explainable
  long-term architecture and the natural next step; the LLM's rule prompt approximates it.
- **Classification head over the 318 seen products**: cannot generalize to the 1,862
  catalog products never chosen historically — rejected because the brief demands the
  function work on *any* requirement data. (Note: 27 of 107 distinct unseen-split test
  targets never appear as train labels, so the split genuinely exercises this.)

## Production notes

- **Suggestion UI over forced top-1**: recall@5 (0.511) is nearly double top-1 retrieval
  accuracy; surfacing 3 candidates with the reranker's confidence and reasoning matches
  how quoting actually works.
- **Cost control**: embeddings and LLM answers are content-hash cached (sqlite);
  the rerank cache ships with the repo, so reviewers replay Method 3 for free.
- **Failure containment**: no key → deterministic cascade; LLM error or out-of-candidate
  answer → retrieval top-1; empty/NaN text → most common historical product; empty input
  frame → empty output. All covered by tests.
- **Exact-history reuse**: in production, an incoming requirement identical to a past one
  could be answered by history directly (a deterministic stage, transparent and cheap).
  We keep it out of the *evaluation* path — that is exactly the leak described above —
  but it is the right first stage in deployment, where 0.894 copy-accuracy is a feature,
  not a bug.

## Repo map

```
data/                          # provided: products.csv (2,180), requirements.csv (1,000)
src/tasks.py                   # deliverable: predict_product_id (+ per-method variants)
src/matching/                  # extraction / sparse / dense / retrieval (RRF) / rerank / pipeline
src/evaluate.py, load_data.py  # provided, untouched
src/evaluation_ext.py          # grouped split, top-k recall, memorization baseline, stage stats
scripts/demo.py                # 10-second smoke test
scripts/run_eval.py            # one command -> results.json + predictions.csv
experiments/01..04_*.py        # kept experiments, chronological
experiments/results/           # results.json, predictions.csv, ablation JSONs
tests/test_tasks.py            # contract tests, no API needed
visualization/                 # original challenge notebooks (untouched)
.cache/rerank.sqlite           # shipped LLM answer cache -> free replay
.env.example                   # OPENAI_API_KEY + pinned model config
```

Build order: experiments 01→04 in sequence, harness first, models second. Two decisions
were reversed by measurement along the way — the leave-one-out precedent fix and the
candidate-list size — and both histories are preserved in the experiments and this document.

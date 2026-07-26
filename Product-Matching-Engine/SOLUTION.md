# Solution — Product Matching System

Matching German construction-tender line items (*Leistungsverzeichnis* positions) to a
Duravit sanitary-product catalog. Three methods of increasing capability, one shared
evaluation framework, every experiment kept per the challenge rules.

## TL;DR results

| Method | Full labeled set | Unseen split* | API cost | Latency (1k rows) |
|---|---|---|---|---|
| 1 — Deterministic cascade (extraction → TF-IDF) | 0.397 | 0.359 | $0 | ~0.3 s |
| 2 — Hybrid retrieval (TF-IDF + BM25 + embeddings, RRF) | 0.295 | 0.273 | <$0.10 (cached) | ~7 s |
| 3 — Full pipeline (extraction → retrieval → LLM selection) | **0.678** | **0.485** | ~$1–2 (cached) | ~2 min |

*Unseen split = duplicate-aware 80/20 group split; precedent index sees only train rows.
Numbers regenerate into `experiments/results/results.json` via `scripts/run_eval.py`
(models: `text-embedding-3-large` @1024 dims, `gpt-5.4-mini`).

How to read this: the extraction stage covers 26.4% of rows at 82.6% precision; hybrid
retrieval puts the target in its top-20 for 68.4% of rows (top-50: 80.4%). Method 3
converts that recall into top-1 accuracy — 0.678 approaches the practical ceiling once
you account for extraction misses and label noise between near-identical variants.
Per-ranker ablation (`experiments/results/retrieval_ablation.json`): char/word TF-IDF
recall@50 0.784, dense embeddings 0.736, BM25 0.605 — RRF fusion beats every single
ranker at 0.804, confirming sparse and dense fail on different rows.

## What the data says (see `experiments/01_eda.py`)

- 2,180 products, 1,000 labeled requirements, only **318 unique targets**; top target
  appears 38×, 158 targets appear exactly once. 171 exact duplicate requirement pairs →
  naive random splits leak; all held-out evaluation here is **group-split by normalized text**.
- **236 rows literally contain the target article number** ("#2527090000",
  "Bestellnummer: 0302490000"). 264 rows contain *some* catalog id; in 225 of those the
  target is among them. This is the highest-precision signal available — but not infallible:
  sometimes the cited number is a component of a larger set that was actually ordered.
- The hard core: Duravit catalogs contain dozens of near-identical variants per series
  (gloss vs silk-matt white, with/without soft-close, coating variants). Tender text rarely
  pins all of these down → an irreducible noise floor for exact-id accuracy.
- Tender idioms matter: "Fabrikat/Typ: Duravit / Starck 3", "oder gleichwertig" (the named
  product is still the anchor), dimension strings ("600 x 460") in 514 rows.

## The three methods

### Method 1 — Deterministic cascade (`predict_product_id_deterministic`)
Regex-extract digit runs (7+) and keep those that exist in the catalog; if any, predict the
first; otherwise fall back to word+char TF-IDF top-1 against the catalog.
**Why it exists:** zero-cost, fully explainable, no external dependency, and it already
captures the strongest signal. This is the floor any fancier method must beat, and the
production-safe fallback when APIs are down.
Development history: `experiments/02_pure_python_baselines.py` (written dependency-free
before any ML: extraction 0.245, char-TF-IDF 0.271 top-1 / 0.485 top-5, cascade **0.382**,
1-NN over history 0.287 LOO but only 0.193 on genuinely unseen text — i.e. history mostly
memorizes).

### Method 2 — Hybrid retrieval (`predict_product_id_hybrid`)
Three rankers over an enriched product document (name + description + category):
- TF-IDF **word(1–2)** and **char_wb(3–5)** — char n-grams handle German compounds
  ("Tiefspülklosett" ≈ "Tiefspül-WC") and partial article numbers,
- **BM25** over normalized tokens — strong on rare exact terms,
- **OpenAI `text-embedding-3-large`** (1024 Matryoshka dims, disk-cached) — paraphrase
  and cross-wording semantics,
fused with **Reciprocal Rank Fusion** (k=60), which needs no score calibration.
Sparse and dense fail in opposite directions; fusion is the standard remedy.
Ablation per ranker: `experiments/03_retrieval_ablation.py`.

### Method 3 — Full pipeline (`predict_product_id`, the deliverable)
1. **Short-circuit:** exactly one extracted article number → predict it (high precision).
2. **Candidate generation:** hybrid top-20 (extracted ids force-included when >1).
3. **Precedents:** top-3 most similar historical requirements with their chosen products —
   the labeled history is evidence of real selection behavior, not just training data.
4. **LLM selection:** `gpt-5-mini`-class model with Structured Outputs picks **one of the
   candidates** under domain rules (series/Fabrikat, product type — seat ≠ bowl —,
   dimensions, Rimless, mounting, color/finish). The model cannot hallucinate an id:
   any out-of-candidate answer falls back to retrieval top-1. All calls disk-cached.

Ablations (`experiments/04_llm_rerank_ablation.py`, 200-row sample, results in
`experiments/results/llm_ablation.json`):

| Variant | Accuracy | Takeaway |
|---|---|---|
| k=20, with precedents | 0.625 | baseline config |
| k=20, **no** precedents | 0.520 | historical precedents are worth **+10.5 pts** |
| k=10, with precedents | 0.580 | too-small candidate lists cap recall |
| k=40, with precedents | **0.685** | recall keeps climbing past top-20 → adopted as default |

The k=40 finding was fed back into `MatcherConfig` — an example of the
measure → change → re-measure loop the whole repo is built around.

## Evaluation methodology (`src/evaluation_ext.py`, `scripts/run_eval.py`)

- **Challenge metric:** the provided `evaluate_product_prediction` on the full set.
- **Unseen split:** 80/20 grouped by normalized text so duplicates never straddle the
  split; the precedent index is rebuilt from train only. This is the honest
  generalization number for anything that consults history.
- **Top-k retrieval recall:** the ceiling for any reranker — if the target isn't in the
  candidate list, no LLM can rescue it.
- **Stage stats:** coverage & precision of the extraction stage; per-category accuracy.
- Reproduce everything: `python scripts/run_eval.py` (add `--no-llm --no-dense` for a
  fully offline run).

## Approaches considered but not implemented (by design, per the brief)

- **Fine-tuned bi-/cross-encoder:** 1,000 labels across 318 classes with 158 singletons is
  too thin to fine-tune without memorizing; would become attractive at ~10k+ labels.
- **Structured attribute extraction:** parse both sides into a schema
  (type, series, dimensions, mounting, color, features) and match structurally — the most
  explainable route and the best long-term architecture for full-catalog coverage, but a
  larger build; the LLM reranker approximates it via its rule prompt.
- **Classification head over 318 seen products:** cheap and decent on frequent classes, but
  cannot generalize to the 1,862 catalog products never chosen historically — rejected
  because the brief demands the function work on *any* requirement data.

## Where the remaining errors live (Method 3)

Per-category accuracy on the full set (k=40 config): Wannen 0.91, Armaturen 0.79,
Keramik 0.73, WC-Sitze 0.65, Badzubehör 0.41, W&W Zubehör 0.27. The weak spots are
exactly the variant-dense segments: accessories and fittings where dozens of articles
differ only in finish/hinge/soft-close — often under-specified in the tender text, so
even a human picker would need a follow-up question. The LLM chose an out-of-candidate
id in only ~1% of rows, all safely caught by the fallback guard.

## Extending to full coverage & production notes

- Retrieval + rerank already covers the entire catalog (nothing is restricted to seen
  targets); accuracy on never-seen products simply lacks precedent evidence.
- The honest error floor is variant ambiguity — in production this becomes a *ranked
  suggestion UI* (top-3 with confidence) rather than a forced top-1; retrieval recall@5
  is far above top-1 accuracy, which is exactly the assistive-quoting workflow.
- Cost control: embeddings and LLM answers are content-hash cached (sqlite); re-runs are
  free and deterministic. Full-dataset Method 3 run costs roughly $1–3 on a mini-tier model.
- Failure containment: every stage degrades gracefully (no key → sparse hybrid; LLM
  error/non-candidate answer → retrieval top-1; empty text → most-common product).

## Repo map

```
src/tasks.py                  # deliverable: predict_product_id (+ per-method variants)
src/matching/                 # extraction, sparse, dense, retrieval (RRF), rerank, pipeline
src/evaluation_ext.py         # grouped split, top-k recall, stage stats
scripts/run_eval.py           # one-command evaluation, writes experiments/results/
experiments/01..04_*.py       # kept experiments, in chronological order
visualization/                # original challenge notebooks (untouched)
```

Setup: `python3 -m venv .venv && .venv/bin/pip install -r requirements.txt`,
copy `.env.example` → `.env` with your `OPENAI_API_KEY` (optional — everything runs
without it, minus the dense ranker and Method 3).

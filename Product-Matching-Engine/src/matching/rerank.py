"""Method 3 building block: LLM reranker over retrieved candidates.

The LLM never generates a product id freely — it selects from the retrieved
candidate list (validated afterwards), which makes hallucination structurally
impossible. Responses are disk-cached by prompt hash.
"""
import logging
import os
import time
from concurrent.futures import ThreadPoolExecutor
from typing import Optional, Sequence

from pydantic import BaseModel

from .cache import DiskCache

logger = logging.getLogger(__name__)

_MODEL_PREFERENCE = ("gpt-5.4-mini", "gpt-5-mini", "gpt-4o-mini")

SYSTEM_PROMPT = """You are an expert sales engineer for Duravit sanitary products. \
You match German construction-tender line items (Leistungsverzeichnis positions) to the \
single best product in the Duravit catalog.

Rules, in priority order:
1. If the requirement cites a Duravit article number (e.g. "#2527090000" or "Bestellnummer"), \
that product is almost always the right answer — unless the text clearly orders a bigger \
assembly/set of which the cited number is only one component.
2. Match the series/model line exactly when named (Starck 3, ME by Starck, DuraStyle, D-Code, \
Vero, Happy D.2, No.1, P3 Comforts, ...). "Fabrikat/Typ" lines name the intended product.
3. Match the product type precisely: Wand-WC vs Stand-WC, Tiefspueler vs Flachspueler, \
WC-Sitz (seat!) vs WC (bowl!), Waschtisch vs Handwaschbecken vs Einbauwaschtisch, \
Urinal, Badewanne, Duschwanne. Never confuse a seat with a bowl.
4. Match dimensions (e.g. 360x540x340, 600 mm), Rimless/spuelrandlos, mounting \
(wandhaengend, bodenstehend), and features (Absenkautomatik, Hahnloch, Ueberlauf).
5. Color/finish variants (Weiss Hochglanz vs Seidenmatt, HygieneGlaze/WonderGliss coating) \
distinguish otherwise identical articles — use them when mentioned, else prefer the standard \
white glossy variant.
6. "oder gleichwertig" (or equivalent) still means the named product is the anchor.
7. Historical precedents show what was actually chosen for similar requirements — they \
reflect real selection behavior, weigh them strongly when the requirement is very similar.

Answer with the product_id of exactly one candidate."""


class RerankChoice(BaseModel):
    product_id: str
    confidence: float
    reasoning: str


def build_user_prompt(
    query: str,
    candidates: Sequence[dict],
    precedents: Sequence[tuple[str, str, str]],
) -> str:
    lines = ["## Requirement\n", query.strip()[:4000], "\n\n## Candidate products\n"]
    for c in candidates:
        lines.append(
            f"- product_id={c['product_id']} | {c['name']} | {c['description']} | {c['category']}\n"
        )
    if precedents:
        lines.append("\n## Historical precedents (similar requirement -> chosen product)\n")
        for text, pid, name in precedents:
            lines.append(f"- \"{text.strip()[:300]}\" -> {pid} ({name})\n")
    lines.append("\nSelect the single best candidate product_id.")
    return "".join(lines)


class LLMReranker:
    def __init__(self, model: Optional[str] = None) -> None:
        from dotenv import load_dotenv
        from openai import OpenAI

        from .dense import _ENV_PATH

        load_dotenv(_ENV_PATH)
        self._client = OpenAI()
        self._cache = DiskCache("rerank")
        self.model = model or os.environ.get("RERANK_MODEL") or self._resolve_model()

    def _resolve_model(self) -> str:
        try:
            available = {m.id for m in self._client.models.list()}
            for candidate in _MODEL_PREFERENCE:
                if candidate in available:
                    return candidate
        except Exception as exc:  # noqa: BLE001 - fall back to safest default
            logger.warning("Could not list models (%s); defaulting to %s", exc, _MODEL_PREFERENCE[-1])
        return _MODEL_PREFERENCE[-1]

    def _call(self, user_prompt: str) -> dict:
        key = self._cache.key(self.model, SYSTEM_PROMPT, user_prompt)
        cached = self._cache.get(key)
        if cached is not None:
            return cached
        for attempt in range(4):
            try:
                resp = self._client.chat.completions.parse(
                    model=self.model,
                    messages=[
                        {"role": "system", "content": SYSTEM_PROMPT},
                        {"role": "user", "content": user_prompt},
                    ],
                    response_format=RerankChoice,
                )
                parsed = resp.choices[0].message.parsed
                if parsed is None:
                    raise ValueError("model returned no parsed content (refusal?)")
                data = parsed.model_dump()
                self._cache.set(key, data)
                return data
            except Exception as exc:  # noqa: BLE001 - retry transient API errors
                if attempt == 3:
                    raise
                wait = 2**attempt
                logger.warning("Rerank call failed (%s); retrying in %ss", exc, wait)
                time.sleep(wait)
        raise RuntimeError("unreachable")

    def choose(
        self,
        query: str,
        candidates: Sequence[dict],
        precedents: Sequence[tuple[str, str, str]],
    ) -> RerankChoice:
        """Pick one candidate; falls back to the top retrieval candidate on any failure."""
        fallback = RerankChoice(product_id=candidates[0]["product_id"], confidence=0.0, reasoning="fallback")
        try:
            data = self._call(build_user_prompt(query, candidates, precedents))
            choice = RerankChoice.model_validate(data)
        except Exception as exc:  # noqa: BLE001 - never let one row break the batch
            logger.warning("Rerank failed for query %.60r: %s", query, exc)
            return fallback
        if choice.product_id not in {c["product_id"] for c in candidates}:
            logger.warning("LLM chose non-candidate %s; using retrieval top-1", choice.product_id)
            return fallback
        return choice

    def choose_batch(
        self,
        queries: Sequence[str],
        candidates_list: Sequence[Sequence[dict]],
        precedents_list: Sequence[Sequence[tuple[str, str, str]]],
        max_workers: int = 8,
    ) -> list[RerankChoice]:
        with ThreadPoolExecutor(max_workers=max_workers) as pool:
            return list(pool.map(self.choose, queries, candidates_list, precedents_list))

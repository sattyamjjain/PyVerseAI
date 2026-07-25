"""OpenAI provider: strict JSON-schema structured outputs.

`chat.completions.parse` converts the Pydantic model to a strict schema
(additionalProperties: false, all fields required) and validates the reply.
Same prompt, same schema, same downstream pipeline as the Anthropic provider —
which is exactly what makes the two comparable in the eval.
"""

from __future__ import annotations

from time import perf_counter

from openai import OpenAI

from .. import config
from ..prompts import SYSTEM_PROMPT, build_user_message
from ..schema import InvoiceExtraction
from .base import ExtractionProvider, ProviderError, ProviderResult


class OpenAIProvider(ExtractionProvider):
    name = "openai"
    supports_vision = False  # PDF input is wired for Claude only; see DECISIONS.md

    def __init__(self, model: str | None = None) -> None:
        self.model = model or config.OPENAI_MODEL
        self._client = OpenAI(max_retries=config.SDK_MAX_RETRIES, timeout=config.REQUEST_TIMEOUT_S)

    def extract_text_mode(self, document_text: str, source_name: str) -> ProviderResult:
        t0 = perf_counter()
        completion = self._client.chat.completions.parse(
            model=self.model,
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": build_user_message(document_text, source_name)},
            ],
            response_format=InvoiceExtraction,
            max_completion_tokens=config.MAX_OUTPUT_TOKENS,
        )
        latency = perf_counter() - t0
        message = completion.choices[0].message
        if getattr(message, "refusal", None):
            raise ProviderError(f"{self.model} refused: {message.refusal}")
        if message.parsed is None:
            raise ProviderError(f"{self.model} returned no parsed output")
        usage = completion.usage
        return ProviderResult(
            extraction=message.parsed,
            provider=self.name,
            model=self.model,
            mode="text",
            input_tokens=usage.prompt_tokens if usage else 0,
            output_tokens=usage.completion_tokens if usage else 0,
            latency_s=latency,
        )

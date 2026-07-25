"""Anthropic provider: native structured outputs via `messages.parse`.

The SDK enforces the schema server-side (grammar-constrained decoding), retries
transient failures itself (`max_retries`), and returns a validated Pydantic
object — so there is no JSON-repair or reask loop here on purpose.

Model-behaviour notes that shaped this code (July 2026):
- No `temperature`/`top_p` on Claude 5 models: non-default values are a 400.
- `output_config={"effort": ...}` is supported on Sonnet 5 but not Haiku 4.5,
  so effort is sent only for models known to accept it.
- PDFs go in as a `document` content block (vision): each page is billed as
  image + text tokens, so this is the fallback path, not the default.
"""

from __future__ import annotations

import base64
from time import perf_counter

from anthropic import Anthropic

from .. import config
from ..prompts import SYSTEM_PROMPT, VISION_TASK_MESSAGE, build_user_message
from ..schema import InvoiceExtraction
from .base import ExtractionProvider, Mode, ProviderError, ProviderResult


class AnthropicProvider(ExtractionProvider):
    name = "anthropic"
    supports_vision = True

    def __init__(self, model: str | None = None) -> None:
        self.model = model or config.ANTHROPIC_MODEL
        self._client = Anthropic(
            max_retries=config.SDK_MAX_RETRIES, timeout=config.REQUEST_TIMEOUT_S
        )

    def extract_text_mode(self, document_text: str, source_name: str) -> ProviderResult:
        content = [{"type": "text", "text": build_user_message(document_text, source_name)}]
        return self._call(content, mode="text")

    def extract_vision_mode(self, pdf_bytes: bytes, source_name: str) -> ProviderResult:
        content = [
            {
                "type": "document",
                "source": {
                    "type": "base64",
                    "media_type": "application/pdf",
                    "data": base64.standard_b64encode(pdf_bytes).decode("ascii"),
                },
            },
            {"type": "text", "text": VISION_TASK_MESSAGE},
        ]
        return self._call(content, mode="vision")

    def _call(self, content: list[dict], mode: Mode) -> ProviderResult:
        kwargs: dict = {}
        if self.model.startswith(config.EFFORT_SUPPORTED_PREFIXES):
            kwargs["output_config"] = {"effort": config.EXTRACTION_EFFORT}
        t0 = perf_counter()
        try:
            response = self._client.messages.parse(
                model=self.model,
                max_tokens=config.MAX_OUTPUT_TOKENS,
                system=SYSTEM_PROMPT,
                messages=[{"role": "user", "content": content}],
                output_format=InvoiceExtraction,
                **kwargs,
            )
        except TypeError:
            # Older SDK without an output_config kwarg on parse(): drop effort.
            kwargs.pop("output_config", None)
            response = self._client.messages.parse(
                model=self.model,
                max_tokens=config.MAX_OUTPUT_TOKENS,
                system=SYSTEM_PROMPT,
                messages=[{"role": "user", "content": content}],
                output_format=InvoiceExtraction,
                **kwargs,
            )
        latency = perf_counter() - t0
        if response.stop_reason == "max_tokens":
            raise ProviderError(
                f"{self.model} hit max_tokens={config.MAX_OUTPUT_TOKENS} — output truncated"
            )
        extraction = response.parsed_output
        if extraction is None:
            raise ProviderError(f"{self.model} returned no parsed output")
        return ProviderResult(
            extraction=extraction,
            provider=self.name,
            model=self.model,
            mode=mode,
            input_tokens=response.usage.input_tokens,
            output_tokens=response.usage.output_tokens,
            latency_s=latency,
        )

"""Mock provider: replays committed fixtures — the $0, keyless, offline path.

Fixtures are the raw model outputs recorded during real runs (one JSON per
document x provider). Replaying them exercises the entire pipeline downstream
of the API call, so `make run-mock` regenerates the committed CSV byte-for-byte
and the test suite runs green with no API key.
"""

from __future__ import annotations

import json

from .. import config
from ..schema import InvoiceExtraction
from .base import ExtractionProvider, ProviderError, ProviderResult


def fixture_path(source_stem: str, provider: str):
    return config.FIXTURES_DIR / f"{source_stem}.{provider}.json"


class MockProvider(ExtractionProvider):
    supports_vision = True  # replays whatever mode the recorded run used

    def __init__(self, target_provider: str = "anthropic") -> None:
        self.target = target_provider
        self.name = f"mock:{target_provider}"
        self.model = f"mock:{target_provider}"

    def _load(self, source_name: str) -> ProviderResult:
        stem = source_name.rsplit(".", 1)[0]
        path = fixture_path(stem, self.target)
        if not path.exists():
            raise ProviderError(
                f"no fixture for '{source_name}' at {path} — record one with a live run "
                f"(make run / make run-openai) or check out the committed fixtures"
            )
        data = json.loads(path.read_text(encoding="utf-8"))
        return ProviderResult(
            extraction=InvoiceExtraction.model_validate(data["extraction"]),
            provider=self.name,
            model=data.get("model", self.model),
            mode=data.get("mode", "text"),
            input_tokens=data.get("input_tokens", 0),
            output_tokens=data.get("output_tokens", 0),
            latency_s=0.0,
        )

    def extract_text_mode(self, document_text: str, source_name: str) -> ProviderResult:
        return self._load(source_name)

    def extract_vision_mode(self, pdf_bytes: bytes, source_name: str) -> ProviderResult:
        return self._load(source_name)

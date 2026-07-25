"""Provider interface: one method, one result shape, zero framework."""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Literal

from ..schema import InvoiceExtraction

Mode = Literal["text", "vision"]


class ProviderError(RuntimeError):
    """Raised when a provider cannot produce a valid extraction."""


@dataclass
class ProviderResult:
    extraction: InvoiceExtraction
    provider: str
    model: str
    mode: Mode
    input_tokens: int
    output_tokens: int
    latency_s: float


class ExtractionProvider(ABC):
    name: str
    supports_vision: bool = False

    @abstractmethod
    def extract_text_mode(self, document_text: str, source_name: str) -> ProviderResult:
        """Extract from a text-layer document."""

    def extract_vision_mode(self, pdf_bytes: bytes, source_name: str) -> ProviderResult:
        raise ProviderError(f"provider '{self.name}' does not support vision mode")

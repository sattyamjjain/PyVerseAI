"""Provider factory."""

from __future__ import annotations

from .base import ExtractionProvider, ProviderError, ProviderResult
from .mock_provider import MockProvider, fixture_path

__all__ = [
    "ExtractionProvider",
    "MockProvider",
    "ProviderError",
    "ProviderResult",
    "fixture_path",
    "get_provider",
]


def get_provider(name: str, mock: bool = False) -> ExtractionProvider:
    if mock:
        return MockProvider(target_provider=name)
    if name == "anthropic":
        from .anthropic_provider import AnthropicProvider

        return AnthropicProvider()
    if name == "openai":
        from .openai_provider import OpenAIProvider

        return OpenAIProvider()
    raise ValueError(f"unknown provider '{name}' (expected 'anthropic' or 'openai')")

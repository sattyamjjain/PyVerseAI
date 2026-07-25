"""Runtime configuration: env vars, model defaults, pricing."""

from __future__ import annotations

import os
from pathlib import Path

from dotenv import load_dotenv

PROJECT_ROOT = Path(__file__).resolve().parents[2]
load_dotenv(PROJECT_ROOT / ".env")

ANTHROPIC_MODEL = os.getenv("ANTHROPIC_MODEL", "claude-sonnet-5")
OPENAI_MODEL = os.getenv("OPENAI_MODEL", "gpt-5.6-terra")

# Claude 5 models use adaptive thinking; "medium" is the documented cost-sensitive
# step-down from the "high" default. Not sent to models that lack the parameter.
EXTRACTION_EFFORT = os.getenv("EXTRACTION_EFFORT", "medium")
EFFORT_SUPPORTED_PREFIXES = ("claude-fable-5", "claude-opus-5", "claude-opus-4", "claude-sonnet-5")

MAX_OUTPUT_TOKENS = 8192
REQUEST_TIMEOUT_S = 180.0
SDK_MAX_RETRIES = 3

# USD per million tokens (input, output). Standard list prices, July 2026.
PRICING_PER_MTOK: dict[str, tuple[float, float]] = {
    "claude-sonnet-5": (3.00, 15.00),
    "claude-haiku-4-5": (1.00, 5.00),
    "gpt-5.6-terra": (2.50, 15.00),
    "gpt-5.6-luna": (1.00, 6.00),
}

FIXTURES_DIR = PROJECT_ROOT / "fixtures" / "responses"
OUTPUTS_DIR = PROJECT_ROOT / "outputs"
SAMPLES_DIR = PROJECT_ROOT / "samples"
GOLDEN_LABELS = PROJECT_ROOT / "eval" / "golden_labels.yaml"


def cost_usd(model: str, input_tokens: int, output_tokens: int) -> float:
    """Cost of one call; 0.0 for unknown models rather than guessing."""
    if model not in PRICING_PER_MTOK:
        return 0.0
    in_rate, out_rate = PRICING_PER_MTOK[model]
    return (input_tokens * in_rate + output_tokens * out_rate) / 1_000_000

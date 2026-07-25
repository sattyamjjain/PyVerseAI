"""Live API smoke tests — opt-in only (cost money, need keys):

uv run pytest -m live
"""

from __future__ import annotations

import os

import pytest

from invoice_extractor import config
from invoice_extractor.pipeline import process_document

pytestmark = pytest.mark.live

BASELINE = config.SAMPLES_DIR / "centralhudson-us-electric-en.pdf"


@pytest.mark.skipif(not os.getenv("ANTHROPIC_API_KEY"), reason="ANTHROPIC_API_KEY not set")
def test_anthropic_extracts_the_baseline_bill():
    from invoice_extractor.providers.anthropic_provider import AnthropicProvider

    outcome = process_document(BASELINE, AnthropicProvider())
    assert outcome.error is None
    row = outcome.rows[0]
    assert row.utility_type == "electricity"
    assert row.usage_unit == "kWh"
    assert row.usage_amount is not None
    assert row.vendor_name and "central hudson" in row.vendor_name.lower()
    assert row.billing_period_start and row.billing_period_start.startswith("2021-")


@pytest.mark.skipif(not os.getenv("OPENAI_API_KEY"), reason="OPENAI_API_KEY not set")
def test_openai_extracts_the_baseline_bill():
    from invoice_extractor.providers.openai_provider import OpenAIProvider

    outcome = process_document(BASELINE, OpenAIProvider())
    assert outcome.error is None
    row = outcome.rows[0]
    assert row.utility_type == "electricity"
    assert row.usage_unit == "kWh"
    assert row.usage_amount is not None

"""Fixture-replay regression tests: the committed raw model responses through
the full downstream pipeline must reproduce the committed CSV exactly.

These are skipped until fixtures exist (they are recorded by the first live
run and committed), after which they run everywhere with no key and no cost."""

from __future__ import annotations

import pytest

from invoice_extractor import config
from invoice_extractor.csv_writer import write_rows
from invoice_extractor.ingest import discover
from invoice_extractor.pipeline import run_pipeline
from invoice_extractor.providers import MockProvider, ProviderError

fixtures_exist = config.FIXTURES_DIR.is_dir() and any(config.FIXTURES_DIR.glob("*.anthropic.json"))


@pytest.mark.skipif(not fixtures_exist, reason="no committed fixtures yet (run `make run` once)")
def test_mock_replay_reproduces_committed_csv(tmp_path):
    committed = config.OUTPUTS_DIR / "invoices.csv"
    if not committed.exists():
        pytest.skip("no committed outputs/invoices.csv yet")
    files = discover([config.SAMPLES_DIR])
    summary = run_pipeline(files, MockProvider("anthropic"), record_fixtures=False, verbose=False)
    regenerated = write_rows(summary.rows, tmp_path / "invoices.csv")
    assert regenerated.read_bytes() == committed.read_bytes(), (
        "mock replay diverged from the committed CSV — either fixtures/outputs are "
        "stale (rerun `make run`) or a post-processing change altered behaviour "
        "(inspect the diff, then regenerate outputs deliberately)"
    )


@pytest.mark.skipif(not fixtures_exist, reason="no committed fixtures yet")
def test_every_sample_has_a_fixture():
    files = discover([config.SAMPLES_DIR])
    missing = [
        f.name for f in files if not (config.FIXTURES_DIR / f"{f.stem}.anthropic.json").exists()
    ]
    assert not missing, f"samples without committed fixtures: {missing}"


def test_missing_fixture_is_a_clear_error(tmp_path):
    provider = MockProvider("anthropic")
    with pytest.raises(ProviderError, match="no fixture"):
        provider.extract_text_mode("whatever", "does-not-exist.pdf")

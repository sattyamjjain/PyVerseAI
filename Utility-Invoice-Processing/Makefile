# Uses uv (https://docs.astral.sh/uv/). No uv? See README "Without uv" for the
# pip equivalents - every target is a one-liner you can run by hand.

.PHONY: setup run run-mock run-openai run-edge run-all eval test test-live lint ui clean

setup:            ## Create venv + install all deps (incl. dev)
	uv sync --all-extras

run:              ## Live extraction of samples/ with Claude -> outputs/invoices.csv
	uv run invoice-extract samples -o outputs/invoices.csv --provider anthropic

run-openai:       ## Same run against OpenAI -> outputs/invoices.openai.csv
	uv run invoice-extract samples -o outputs/invoices.openai.csv --provider openai

run-mock:         ## Offline replay of committed fixtures (no API key, $0)
	uv run invoice-extract samples -o outputs/invoices.csv --provider anthropic --mock

run-edge:         ## Live run including the deliberate edge-case bills
	uv run invoice-extract samples --edge-cases -o outputs/invoices_edge.csv --provider anthropic

eval:             ## Score outputs against hand-labeled golden data -> outputs/eval_report.md
	uv run invoice-eval

test:             ## Unit + fixture-replay tests. No API key needed, no network.
	uv run pytest

test-live:        ## Also run the live API smoke tests (needs .env keys)
	uv run pytest -m live

lint:             ## Ruff lint + format check
	uv run ruff check src tests app && uv run ruff format --check src tests app

ui:               ## Launch the Streamlit review UI
	uv run --extra ui streamlit run app/streamlit_app.py

clean:
	rm -rf .venv .pytest_cache .ruff_cache

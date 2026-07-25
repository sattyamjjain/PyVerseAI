"""Streamlit review UI — the human side of the confidence loop.

Fields the pipeline marks `review` (ambiguous status, unverified quote, failed
validation rule) need a person; this is where that person works: extracted
fields next to the document text, evidence quotes, and status badges.

    make ui            # or: uv run --extra ui streamlit run app/streamlit_app.py
"""

from __future__ import annotations

import json
import os
import sys
from pathlib import Path

import streamlit as st

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from invoice_extractor import config  # noqa: E402
from invoice_extractor.ingest import extract_text  # noqa: E402
from invoice_extractor.pipeline import process_document  # noqa: E402
from invoice_extractor.providers import get_provider  # noqa: E402

st.set_page_config(page_title="Utility Invoice Extractor", page_icon="⚡", layout="wide")

STATUS_BADGE = {
    "confident": "🟢 confident",
    "ambiguous": "🟡 ambiguous",
    "inferred": "🟡 inferred",
    "not_found": "⚪ not found",
}


def available_samples() -> list[Path]:
    files = sorted(config.SAMPLES_DIR.glob("*.pdf"))
    files += sorted((config.SAMPLES_DIR / "edge_cases").glob("*.pdf"))
    return files


st.title("⚡ Utility Invoice Extractor — review console")

with st.sidebar:
    st.header("Run settings")
    have_key = bool(os.getenv("ANTHROPIC_API_KEY") or os.getenv("OPENAI_API_KEY"))
    mock = st.toggle(
        "Offline mode (replay committed fixtures)",
        value=not have_key,
        help="No API key needed; replays the recorded model responses.",
    )
    provider_name = st.radio("Provider", ["anthropic", "openai"], horizontal=True)
    model = config.ANTHROPIC_MODEL if provider_name == "anthropic" else config.OPENAI_MODEL
    st.caption(f"Model: `{model}`")
    selected = st.selectbox("Invoice", available_samples(), format_func=lambda p: p.name, index=0)
    run = st.button("Extract", type="primary", use_container_width=True)

if run and selected:
    provider = get_provider(provider_name, mock=mock)
    with st.spinner(f"Extracting {selected.name}…"):
        outcome = process_document(selected, provider)
    st.session_state["outcome"] = outcome
    st.session_state["doc_text"] = extract_text(selected).text

outcome = st.session_state.get("outcome")
if outcome is None:
    st.info("Pick an invoice on the left and hit **Extract**.")
else:
    detail = outcome.detail
    if outcome.error:
        st.error(f"Extraction failed: {outcome.error}")
    else:
        mode = detail.get("mode", "text")
        cost = detail.get("cost_usd", 0.0)
        st.caption(
            f"`{outcome.source_file}` · {detail.get('model')} · mode **{mode}** · "
            f"lang **{detail.get('language') or '?'}** · ${cost:.4f}"
        )
        left, right = st.columns([1, 1])

        with left:
            st.subheader("Extracted fields")
            for name, info in detail.get("fields", {}).items():
                badge = STATUS_BADGE.get(info["status"], info["status"])
                verified = info.get("quote_verified")
                check = "" if verified is None else (" · quote ✅" if verified else " · quote ❌")
                st.markdown(f"**{name}** — {badge}{check}")
                st.code(str(info["value"]), language=None)
                if info.get("source_quote"):
                    st.caption(f"“{info['source_quote']}”")
            st.subheader("Readings")
            for row, rdetail in zip(outcome.rows, detail.get("readings", []), strict=False):
                with st.container(border=True):
                    status_icon = "🟢" if row.extraction_status == "ok" else "🟡"
                    st.markdown(
                        f"{status_icon} **{row.utility_type}** — "
                        f"{row.usage_amount or '∅'} {row.usage_unit or ''} · "
                        f"{row.billing_period_start or '?'} → {row.billing_period_end or '?'}"
                    )
                    if rdetail.get("usage_quote"):
                        st.caption(f"usage: “{rdetail['usage_quote']}”")
                    if row.validation_flags:
                        st.warning("  \n".join(row.validation_flags.split(";")))

        with right:
            st.subheader("Document text (as the model saw it)")
            text = st.session_state.get("doc_text", "")
            if detail.get("mode") == "vision":
                st.info(
                    "Image-only bill: extracted via native PDF/vision input. "
                    "The text layer below lacks the figures — which is why."
                )
            st.text_area("text", text, height=520, label_visibility="collapsed")

        st.divider()
        st.subheader("Row(s) for the CSV")
        st.dataframe([r.as_csv_dict() for r in outcome.rows], use_container_width=True)

csv_path = config.OUTPUTS_DIR / "invoices.csv"
if csv_path.exists():
    st.divider()
    st.subheader("Latest full-run CSV")
    st.download_button(
        "Download invoices.csv", csv_path.read_bytes(), file_name="invoices.csv", mime="text/csv"
    )
    report_path = config.OUTPUTS_DIR / "run_report.json"
    if report_path.exists():
        report = json.loads(report_path.read_text())
        st.caption(
            f"{report['files']} files → {report['rows']} rows · "
            f"${report.get('cost_usd', 0):.4f} · {report.get('wall_s', '?')}s · "
            f"languages: {', '.join(report.get('languages', []))}"
        )

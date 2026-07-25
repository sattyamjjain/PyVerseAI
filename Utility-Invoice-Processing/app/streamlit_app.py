"""Streamlit review console — the human side of the confidence loop.

Fields the pipeline marks `review` (ambiguous status, unverified quote, failed
validation rule) need a person; this is where that person works: extracted
fields beside the source text, evidence quotes, and status badges.

    make ui            # or: uv run --extra ui streamlit run app/streamlit_app.py
"""

from __future__ import annotations

import csv
import html
import json
import re
import sys
from pathlib import Path

import streamlit as st

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from invoice_extractor import config  # noqa: E402
from invoice_extractor.ingest import extract_text  # noqa: E402
from invoice_extractor.pipeline import process_document  # noqa: E402
from invoice_extractor.providers import get_provider  # noqa: E402

st.set_page_config(page_title="Utility Invoice Extractor", page_icon="⚡", layout="wide")

# --- look & feel -----------------------------------------------------------

CSS = """
<style>
header[data-testid="stHeader"], #MainMenu, footer,
[data-testid="stToolbar"], [data-testid="stDecoration"], .stDeployButton {
    display: none !important;
}
.block-container { padding-top: 2.2rem; padding-bottom: 3rem; max-width: 1440px; }
section[data-testid="stSidebar"] { border-right: 1px solid #1E2634; }
section[data-testid="stSidebar"] .block-container { padding-top: 1.6rem; }

p.brand { font-size: 30px !important; font-weight: 800; letter-spacing: -0.02em;
          line-height: 1.15; margin: 0 !important; }
section[data-testid="stSidebar"] p.brand { font-size: 22px !important; }
.brand .accent { color: #F59E0B; }
p.tagline { color: #8B95A7 !important; font-size: 14px !important; margin: 2px 0 0 0 !important; }

.sec { font-size: 12px; font-weight: 700; letter-spacing: 0.12em; color: #8B95A7;
       text-transform: uppercase; margin: 6px 0 10px 0; }

.pill { display: inline-flex; align-items: center; gap: 5px; padding: 2px 10px;
        border-radius: 999px; font-size: 11.5px; font-weight: 600; line-height: 1.7;
        border: 1px solid transparent; white-space: nowrap; }
.pill.ok      { background: #10321F; color: #4ADE80; border-color: #1E5232; }
.pill.warn    { background: #3A2A08; color: #FBBF24; border-color: #6B4E0E; }
.pill.err     { background: #3B1214; color: #F87171; border-color: #6E2224; }
.pill.neutral { background: #1B2231; color: #9CA8BC; border-color: #2A3446; }
.pill.accent  { background: #33240A; color: #F59E0B; border-color: #6B4E0E; }
.pill.mono    { font-family: ui-monospace, SFMono-Regular, Menlo, monospace; font-weight: 500; }

.chiprow { display: flex; flex-wrap: wrap; gap: 6px; margin: 8px 0 18px 0; }

.card { background: #131926; border: 1px solid #232D40; border-radius: 14px;
        padding: 14px 18px; margin-bottom: 12px; }
.card .head { display: flex; align-items: center; justify-content: space-between;
              gap: 10px; flex-wrap: wrap; }
.fname { font-family: ui-monospace, SFMono-Regular, Menlo, monospace; font-size: 12.5px;
         color: #8B95A7; }
.fvalue { font-size: 19px; font-weight: 650; margin: 6px 0 2px 0; color: #EDF1F7;
          overflow-wrap: anywhere; }
.fvalue.missing { color: #5B6474; font-weight: 500; font-style: italic; }
.quote { border-left: 3px solid #F59E0B66; margin: 8px 0 0 0; padding: 3px 10px;
         color: #7E8AA0; font-size: 12px;
         font-family: ui-monospace, SFMono-Regular, Menlo, monospace;
         overflow-wrap: anywhere; }

.usage-big { font-size: 30px; font-weight: 750; letter-spacing: -0.02em;
             color: #EDF1F7; margin: 6px 0 0 0; }
.usage-big .unit { font-size: 16px; font-weight: 600; color: #9CA8BC; margin-left: 4px; }
.period { color: #9CA8BC; font-size: 13.5px; margin: 2px 0 8px 0; }

.docpane { max-height: 660px; overflow-y: auto; background: #0B0F17;
           border: 1px solid #232D40; border-radius: 14px; padding: 16px 18px;
           font-family: ui-monospace, SFMono-Regular, Menlo, monospace;
           font-size: 12px; line-height: 1.6; color: #B9C3D4; white-space: pre-wrap; }
.banner { background: #1A2233; border: 1px solid #F59E0B55; border-radius: 12px;
          padding: 10px 14px; font-size: 13px; color: #D8DEE9; margin-bottom: 10px; }

.empty { background: #131926; border: 1px dashed #2A3446; border-radius: 16px;
         padding: 28px 32px; color: #B9C3D4; font-size: 14.5px; line-height: 1.9; }
.empty b { color: #EDF1F7; }
div[data-testid="stMetric"] { background: #131926; border: 1px solid #232D40;
                              border-radius: 12px; padding: 10px 14px; }
</style>
"""
st.markdown(CSS, unsafe_allow_html=True)

esc = html.escape
_CID = re.compile(r"\(cid:\d+\)")

STATUS_KIND = {"confident": "ok", "ambiguous": "warn", "inferred": "warn", "not_found": "neutral"}
ROW_KIND = {"ok": "ok", "review": "warn", "failed": "err"}
UTILITY_ICON = {"electricity": "⚡", "gas": "🔥", "water": "💧", "sewer": "🚰", "other": "📄"}

LABELS = {
    "centralhudson-us-electric-en.pdf": "🇺🇸 Central Hudson · electricity · EN",
    "edf-fr-electricity-fr.pdf": "🇫🇷 EDF · image-only → vision · FR",
    "exodo-es-electricity-es.pdf": "🇪🇸 Iberdrola · genuine invoice · ES",
    "midamerican-us-electric-en.pdf": "🇺🇸 MidAmerican · electricity + gas · EN",
    "sfpuc-us-water-en.pdf": "🇺🇸 SFPUC · water + sewer · EN",
    "swm-de-electricity-de.pdf": "🇩🇪 Stadtwerke München · electricity · DE",
    "vialis-fr-electricity-fr.pdf": "🇫🇷 Vialis · electricity · FR",
    "weenergies-us-electric-gas-en.pdf": "🇺🇸 We Energies · electricity + gas · EN",
    "cub-comed-us-electric-es.pdf": "⚠️ CUB/ComEd · trap: placeholder dates · ES",
    "lapalma-es-electricity-es.pdf": "⚠️ La Palma · trap: contradictory period · ES",
    "ppl-us-electric-en.pdf": "⚠️ PPL · trap: year-less period · EN",
}


def clean_text(text: str) -> tuple[str, bool]:
    """Replace unmapped-glyph tokens ('(cid:NN)') with spaces for display."""
    had_cid = bool(_CID.search(text))
    if had_cid:
        text = re.sub(r"(?:\s*\(cid:\d+\)\s*)+", " ", text)
    return text, had_cid


def pill(text: str, kind: str = "neutral", mono: bool = False) -> str:
    klass = f"pill {kind}" + (" mono" if mono else "")
    return f'<span class="{klass}">{esc(str(text))}</span>'


def field_card(name: str, info: dict) -> str:
    badges = [pill(info["status"], STATUS_KIND.get(info["status"], "neutral"))]
    if info.get("quote_verified") is True:
        badges.append(pill("evidence ✓", "ok"))
    elif info.get("quote_verified") is False and info.get("value") is not None:
        badges.append(pill("evidence ✗", "err"))
    value = info.get("value")
    value_html = (
        f'<div class="fvalue">{esc(str(value))}</div>'
        if value is not None
        else '<div class="fvalue missing">— not on document</div>'
    )
    quote_html = ""
    if info.get("source_quote"):
        quote, _ = clean_text(str(info["source_quote"]))
        quote_html = f'<div class="quote">“{esc(quote)}”</div>'
    return (
        f'<div class="card"><div class="head"><span class="fname">{esc(name)}</span>'
        f"<span>{''.join(badges)}</span></div>{value_html}{quote_html}</div>"
    )


def reading_card(row, rdetail: dict) -> str:
    icon = UTILITY_ICON.get(row.utility_type or "other", "📄")
    head = [
        pill(f"{icon} {row.utility_type or 'no commodity'}", "accent"),
        pill(row.extraction_status, ROW_KIND.get(row.extraction_status, "neutral")),
    ]
    usage = (
        f'<div class="usage-big">{esc(row.usage_amount)}<span class="unit">'
        f"{esc(row.usage_unit or '')}</span></div>"
        if row.usage_amount is not None
        else '<div class="fvalue missing">no usage stated</div>'
    )
    period = (
        f'<div class="period">{esc(row.billing_period_start or "?")} → '
        f"{esc(row.billing_period_end or '?')}</div>"
    )
    meta = []
    if row.usage_source and row.usage_source != "not_found":
        meta.append(pill(f"source: {row.usage_source}", "neutral"))
    if row.read_type and row.read_type != "unknown":
        meta.append(pill(f"read: {row.read_type}", "neutral"))
    if row.meter_id:
        meta.append(pill(f"meter {row.meter_id}", "neutral", mono=True))
    quote_html = ""
    if rdetail.get("usage_quote"):
        quote, _ = clean_text(str(rdetail["usage_quote"]))
        quote_html = f'<div class="quote">“{esc(quote)}”</div>'
    flags = [pill(f"⚑ {f}", "warn", mono=True) for f in rdetail.get("flags", [])]
    flags_html = (
        f'<div class="chiprow" style="margin:10px 0 0 0">{"".join(flags)}</div>' if flags else ""
    )
    return (
        f'<div class="card"><div class="head"><span>{"".join(head)}</span>'
        f"<span>{''.join(meta)}</span></div>{usage}{period}{quote_html}{flags_html}</div>"
    )


def available_samples() -> list[Path]:
    files = sorted(config.SAMPLES_DIR.glob("*.pdf"))
    files += sorted((config.SAMPLES_DIR / "edge_cases").glob("*.pdf"))
    return files


# --- sidebar ---------------------------------------------------------------

with st.sidebar:
    st.markdown(
        '<p class="brand">⚡ Invoice<span class="accent">Extractor</span></p>',
        unsafe_allow_html=True,
    )
    st.markdown(
        '<p class="tagline">multilingual utility bills → validated CSV</p>', unsafe_allow_html=True
    )
    st.markdown(
        '<div class="sec" style="margin-top:22px">Run settings</div>', unsafe_allow_html=True
    )
    mock = st.toggle(
        "Offline · replay recorded responses",
        value=True,
        help="Replays the committed model outputs: instant and free. "
        "Turn off for a live API call (~$0.05/invoice).",
    )
    provider_name = st.radio(
        "Provider",
        ["anthropic", "openai"],
        horizontal=True,
        format_func=lambda p: "Claude" if p == "anthropic" else "OpenAI",
    )
    model = config.ANTHROPIC_MODEL if provider_name == "anthropic" else config.OPENAI_MODEL
    st.markdown(pill(model, "neutral", mono=True), unsafe_allow_html=True)

    st.markdown('<div class="sec" style="margin-top:22px">Invoice</div>', unsafe_allow_html=True)
    selected = st.selectbox(
        "Invoice",
        available_samples(),
        format_func=lambda p: LABELS.get(p.name, p.name),
        label_visibility="collapsed",
    )
    run = st.button("Extract →", type="primary", use_container_width=True)
    st.caption(f"`{selected.name}`" if selected else "")
    st.divider()
    st.caption(
        "8 real bills + 3 traps · 4 languages · every number reproducible "
        "offline from committed fixtures"
    )

# --- header ----------------------------------------------------------------

st.markdown(
    '<p class="brand">Utility Invoice <span class="accent">Extractor</span></p>',
    unsafe_allow_html=True,
)
st.markdown(
    '<p class="tagline">schema-enforced LLM extraction · verbatim-evidence verification · '
    "human-review console</p>",
    unsafe_allow_html=True,
)
st.write("")

if run and selected:
    provider = get_provider(provider_name, mock=mock)
    with st.spinner(f"Extracting {selected.name} …"):
        outcome = process_document(selected, provider)
    st.session_state["outcome"] = outcome
    st.session_state["doc_text"] = extract_text(selected).text

outcome = st.session_state.get("outcome")

if outcome is None:
    st.markdown(
        '<div class="empty"><b>Pick an invoice on the left and hit Extract.</b><br>'
        "A good demo order:<br>"
        "1️⃣ <b>We Energies</b> — combined bill → one row per commodity, all evidence verified<br>"
        "2️⃣ <b>Central Hudson</b> — the confidence loop flagging a real extraction trap<br>"
        "3️⃣ <b>EDF</b> — image-only PDF → automatic vision fallback<br>"
        "4️⃣ <b>CUB/ComEd</b> — placeholder-date trap → honest nulls, no hallucination<br>"
        "5️⃣ flip <b>Offline</b> off → live API call on the Iberdrola production invoice</div>",
        unsafe_allow_html=True,
    )
elif outcome.error:
    st.error(f"Extraction failed: {outcome.error}")
else:
    detail = outcome.detail
    chips = [
        pill(outcome.source_file, "neutral", mono=True),
        pill(detail.get("model", "?"), "neutral", mono=True),
        pill(
            f"mode: {detail.get('mode', 'text')}",
            "accent" if detail.get("mode") == "vision" else "neutral",
        ),
        pill(f"lang: {detail.get('language') or '?'}", "neutral"),
        pill(f"{detail.get('n_pages', '?')} pages", "neutral"),
    ]
    if detail.get("latency_s"):
        chips.append(pill(f"{detail['latency_s']:.1f}s", "neutral"))
    if detail.get("cost_usd"):
        chips.append(pill(f"${detail['cost_usd']:.4f}", "neutral"))
    statuses = {r.extraction_status for r in outcome.rows}
    overall = "failed" if "failed" in statuses else ("review" if "review" in statuses else "ok")
    chips.append(
        pill(
            {"ok": "✓ clean", "review": "needs review", "failed": "failed"}[overall],
            ROW_KIND[overall],
        )
    )
    st.markdown(f'<div class="chiprow">{"".join(chips)}</div>', unsafe_allow_html=True)

    left, right = st.columns([11, 9], gap="large")

    with left:
        st.markdown('<div class="sec">Extracted fields</div>', unsafe_allow_html=True)
        for name, info in detail.get("fields", {}).items():
            st.markdown(field_card(name, info), unsafe_allow_html=True)

        st.markdown(
            '<div class="sec" style="margin-top:20px">Readings — one row per commodity</div>',
            unsafe_allow_html=True,
        )
        rdetails = detail.get("readings", [])
        for i, row in enumerate(outcome.rows):
            rdetail = (
                rdetails[i]
                if i < len(rdetails)
                else {"flags": row.validation_flags.split(";") if row.validation_flags else []}
            )
            st.markdown(reading_card(row, rdetail), unsafe_allow_html=True)
        if detail.get("notes"):
            st.markdown(
                f'<div class="quote" style="margin-top:4px">model note: {esc(detail["notes"])}</div>',
                unsafe_allow_html=True,
            )

    with right:
        st.markdown(
            '<div class="sec">Source document — as the model saw it</div>', unsafe_allow_html=True
        )
        if detail.get("mode") == "vision":
            st.markdown(
                '<div class="banner">🖼️ Image-only bill: the figures live in page images, not this '
                "text layer — extraction went through the model's native PDF (vision) input, and "
                "evidence quotes are marked unverifiable by design.</div>",
                unsafe_allow_html=True,
            )
        text = st.session_state.get("doc_text", "")
        shown, had_cid = clean_text(text)
        if had_cid:
            st.markdown(
                '<div class="banner">⚠️ This PDF embeds an unmapped font: some glyphs reach the text '
                "layer as opaque tokens (cleaned here for display). This is exactly the kind of "
                "real-world extraction hazard the evidence checks exist for.</div>",
                unsafe_allow_html=True,
            )
        if len(shown) > 20_000:
            shown = shown[:20_000] + f"\n… [{len(shown) - 20_000:,} more characters]"
        st.markdown(f'<div class="docpane">{esc(shown)}</div>', unsafe_allow_html=True)

# --- batch results ---------------------------------------------------------

csv_path = config.OUTPUTS_DIR / "invoices.csv"
if csv_path.exists():
    st.write("")
    st.markdown('<div class="sec">Batch run — committed results</div>', unsafe_allow_html=True)
    with csv_path.open(encoding="utf-8-sig") as fh:
        rows = list(csv.DictReader(fh))

    chips = []
    report_path = config.OUTPUTS_DIR / "run_report.anthropic.json"
    if report_path.exists():
        report = json.loads(report_path.read_text())
        chips += [
            pill(f"{report['files']} bills → {report['rows']} rows", "neutral"),
            pill(" · ".join(report.get("languages", [])), "neutral"),
            pill(f"${report.get('cost_usd', 0):.2f} total", "neutral"),
        ]
    eval_path = config.OUTPUTS_DIR / "eval_report.md"
    if eval_path.exists():
        match = re.search(r"\*\*overall\*\*.*\*\*([\d.]+)%\*\*", eval_path.read_text())
        if match:
            chips.append(
                pill(f"measured accuracy {match.group(1)}% vs hand-labeled golden data", "ok")
            )
    st.markdown(f'<div class="chiprow">{"".join(chips)}</div>', unsafe_allow_html=True)

    display_cols = [
        "source_file",
        "utility_type",
        "usage_amount",
        "usage_unit",
        "billing_period_start",
        "billing_period_end",
        "vendor_name",
        "language",
        "extraction_status",
        "validation_flags",
    ]
    st.dataframe(
        [{c: r.get(c, "") for c in display_cols} for r in rows],
        use_container_width=True,
        height=310,
    )
    st.download_button(
        "⬇ Download invoices.csv",
        csv_path.read_bytes(),
        file_name="invoices.csv",
        mime="text/csv",
    )

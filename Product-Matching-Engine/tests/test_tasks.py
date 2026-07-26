"""Contract tests for the deliverable: works on ANY requirement data, no API needed.

Run: .venv/bin/python -m pytest tests/ -q
Everything here uses dense-free matchers, so no OPENAI_API_KEY is required.
"""
import os
import sys

import pandas as pd
import pytest

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.load_data import load_products, load_requirements
from src.matching.pipeline import Matcher, MatcherConfig


@pytest.fixture(scope="module")
def matcher() -> Matcher:
    return Matcher(
        products=load_products(),
        precedents=load_requirements(),
        config=MatcherConfig(use_dense=False, use_precedents=False),
    )


@pytest.fixture(scope="module")
def catalog_ids() -> frozenset:
    return frozenset(load_products()["product_id"])


SYNTHETIC = pd.DataFrame(
    {
        "requirement": [
            "Wand-Tiefspül-WC spülrandlos Duravit Starck 3",
            "Waschtisch 600 x 460 mm weiß",
            "WC-Sitz mit Absenkautomatik",
            None,
            "Produkt laut Bestellnummer 0302490000",
        ],
        "requirement_detail": [
            "Tiefspüler wandhängend, 4,5 Liter, weiß",
            None,
            "Scharniere Edelstahl, abnehmbar",
            None,
            "liefern und montieren",
        ],
    }
)


def _check_contract(preds, df, catalog_ids) -> None:
    preds = list(preds)
    assert len(preds) == len(df)
    assert all(isinstance(p, str) for p in preds)
    assert all(p in catalog_ids for p in preds)


def test_deterministic_on_synthetic_data(matcher, catalog_ids):
    preds = matcher.predict_deterministic(SYNTHETIC)
    _check_contract(preds, SYNTHETIC, catalog_ids)
    assert preds[4] == "0302490000"  # cited article number wins


def test_hybrid_on_synthetic_data(matcher, catalog_ids):
    _check_contract(matcher.predict_hybrid(SYNTHETIC), SYNTHETIC, catalog_ids)


def test_empty_dataframe(matcher):
    empty = pd.DataFrame({"requirement": [], "requirement_detail": []})
    assert matcher.predict_deterministic(empty) == []
    assert matcher.predict_hybrid(empty) == []


def test_order_preserved(matcher):
    reqs = load_requirements().head(6)
    df = reqs[["requirement", "requirement_detail"]]
    forward = matcher.predict_deterministic(df)
    backward = matcher.predict_deterministic(df.iloc[::-1])
    assert forward == backward[::-1]


def test_deterministic_is_deterministic(matcher):
    df = load_requirements().head(10)[["requirement", "requirement_detail"]]
    assert matcher.predict_deterministic(df) == matcher.predict_deterministic(df)


def test_alphanumeric_article_numbers(matcher, catalog_ids):
    alnum = next(pid for pid in catalog_ids if not pid.isdigit())
    df = pd.DataFrame({"requirement": [f"Fabrikat DURAVIT Typ {alnum}"], "requirement_detail": [""]})
    assert matcher.predict_deterministic(df) == [alnum]


def test_small_catalog():
    small = Matcher(products=load_products().head(3), config=MatcherConfig(use_dense=False))
    df = pd.DataFrame({"requirement": ["Ablaufgarnitur"], "requirement_detail": [""]})
    preds = small.predict_hybrid(df)
    assert len(preds) == 1


def test_evaluate_integration(matcher):
    from src.evaluate import evaluate_product_prediction

    data = load_requirements().head(50)
    acc = evaluate_product_prediction(data, matcher.predict_deterministic)
    assert 0.0 <= acc <= 1.0

"""Text normalization helpers for German sanitary-product texts."""
import re

import pandas as pd

_UMLAUTS = str.maketrans({"ä": "ae", "ö": "oe", "ü": "ue", "ß": "ss"})


def normalize(text: str) -> str:
    """Lowercase, fold German umlauts, collapse whitespace/punctuation noise."""
    text = str(text).lower().translate(_UMLAUTS)
    text = re.sub(r"[#/]", " ", text)
    text = re.sub(r"\s+", " ", text)
    return text.strip()


def requirement_text(df: pd.DataFrame) -> pd.Series:
    """Combine requirement + requirement_detail into a single query string."""
    req = df["requirement"].fillna("").astype(str)
    detail = df["requirement_detail"].fillna("").astype(str)
    return (req + " " + detail).str.strip()


def product_doc(products: pd.DataFrame) -> pd.Series:
    """Build one searchable document per catalog product."""
    return (
        products["name"].fillna("")
        + " " + products["description"].fillna("")
        + " " + products["category"].fillna("")
    ).str.strip()

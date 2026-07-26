"""Method 1 building block: deterministic article-number extraction.

Tender texts frequently embed the Duravit article number directly
("Hersteller / Typ: Duravit / Starck 3 #2527090000", "Bestellnummer: 0302490000").
Any digit run of 7+ chars that exists in the catalog is treated as a candidate.
This is the highest-precision signal in the dataset (~26% coverage).
"""
import re
from typing import Iterable

_ID_PATTERN = re.compile(r"\d{7,}")


def extract_catalog_ids(text: str, catalog_ids: frozenset[str]) -> list[str]:
    """Return unique catalog product_ids literally present in the text, in order."""
    seen: set[str] = set()
    out: list[str] = []
    for token in _ID_PATTERN.findall(str(text)):
        if token in catalog_ids and token not in seen:
            seen.add(token)
            out.append(token)
    return out


def extract_all(texts: Iterable[str], catalog_ids: frozenset[str]) -> list[list[str]]:
    return [extract_catalog_ids(t, catalog_ids) for t in texts]

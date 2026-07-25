"""Document discovery and text extraction (text-layer PDFs and .txt files).

pdfplumber with layout=True approximates the visual arrangement of the page,
which matters on invoices: meaning is carried by position (label left, value
right; charges left column, meter data right column). OCR is out of scope by
assessment definition; image-only PDFs are handled by the vision fallback.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from pathlib import Path

import pdfplumber

# pdfminer is chatty about imperfect PDFs (CropBox warnings etc.)
logging.getLogger("pdfminer").setLevel(logging.ERROR)

SUPPORTED_SUFFIXES = {".pdf", ".txt"}


@dataclass
class IngestedDoc:
    path: Path
    text: str
    n_pages: int

    @property
    def n_chars(self) -> int:
        return len(self.text.strip())


def discover(inputs: list[Path], include_edge_cases: bool = False) -> list[Path]:
    """Expand files/directories into a sorted, deduplicated document list."""
    found: list[Path] = []
    for item in inputs:
        if item.is_dir():
            found.extend(p for p in item.iterdir() if p.suffix.lower() in SUPPORTED_SUFFIXES)
            edge = item / "edge_cases"
            if include_edge_cases and edge.is_dir():
                found.extend(p for p in edge.iterdir() if p.suffix.lower() in SUPPORTED_SUFFIXES)
        elif item.suffix.lower() in SUPPORTED_SUFFIXES:
            found.append(item)
        else:
            raise FileNotFoundError(f"not a PDF/TXT file or directory: {item}")
    return sorted(set(found), key=lambda p: p.name)


def extract_text(path: Path) -> IngestedDoc:
    if path.suffix.lower() == ".txt":
        return IngestedDoc(path=path, text=path.read_text(encoding="utf-8"), n_pages=1)
    pages: list[str] = []
    with pdfplumber.open(path) as pdf:
        for page in pdf.pages:
            pages.append(page.extract_text(layout=True) or "")
    return IngestedDoc(path=path, text="\n\n".join(pages), n_pages=len(pages))

"""Dense retrieval: OpenAI embeddings with a persistent disk cache.

Uses text-embedding-3-large truncated to 1024 dims (Matryoshka) — near-full
quality at 1/3 of the storage/compute. Every embedding is cached by content
hash, so repeated runs cost nothing.
"""
import logging
import os
import time
from typing import Optional, Sequence

import numpy as np

from .cache import DiskCache

logger = logging.getLogger(__name__)

_ENV_PATH = os.path.join(
    os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), ".env"
)

EMBED_MODEL = os.environ.get("EMBED_MODEL", "text-embedding-3-large")
EMBED_DIMS = int(os.environ.get("EMBED_DIMS", "1024"))
_BATCH = 256


def has_openai_key() -> bool:
    try:
        from dotenv import load_dotenv

        load_dotenv(_ENV_PATH)
    except ImportError:
        pass
    return bool(os.environ.get("OPENAI_API_KEY"))


class Embedder:
    def __init__(self) -> None:
        from dotenv import load_dotenv
        from openai import OpenAI

        load_dotenv(_ENV_PATH)
        self._client = OpenAI()
        self._cache = DiskCache("embeddings")

    def _fetch_batch(self, texts: list[str]) -> list[list[float]]:
        for attempt in range(4):
            try:
                resp = self._client.embeddings.create(
                    model=EMBED_MODEL, input=texts, dimensions=EMBED_DIMS
                )
                return [d.embedding for d in resp.data]
            except Exception as exc:  # noqa: BLE001 - retry any transient API error
                if attempt == 3:
                    raise
                wait = 2**attempt
                logger.warning("Embedding batch failed (%s); retrying in %ss", exc, wait)
                time.sleep(wait)
        raise RuntimeError("unreachable")

    def embed(self, texts: Sequence[str]) -> np.ndarray:
        """Embed texts (cached), returning an L2-normalized (n, dims) matrix."""
        texts = [t if t.strip() else "leer" for t in texts]
        keys = [self._cache.key(EMBED_MODEL, str(EMBED_DIMS), t) for t in texts]
        vectors: list[Optional[list[float]]] = [self._cache.get(k) for k in keys]
        missing = [i for i, v in enumerate(vectors) if v is None]
        for start in range(0, len(missing), _BATCH):
            idx = missing[start : start + _BATCH]
            for i, vec in zip(idx, self._fetch_batch([texts[i] for i in idx])):
                vectors[i] = vec
                self._cache.set(keys[i], vec)
        mat = np.asarray(vectors, dtype=np.float32)
        norms = np.linalg.norm(mat, axis=1, keepdims=True)
        return mat / np.clip(norms, 1e-9, None)

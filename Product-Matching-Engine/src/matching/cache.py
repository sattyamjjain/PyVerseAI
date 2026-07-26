"""Tiny sqlite-backed disk cache for API responses (embeddings, LLM calls).

Keeps re-runs free and deterministic: every OpenAI response is cached by a
content hash, so evaluating twice never re-bills or changes results.
"""
import hashlib
import json
import os
import sqlite3
import threading
from typing import Any, Optional

_BASE = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), ".cache")


class DiskCache:
    def __init__(self, name: str) -> None:
        os.makedirs(_BASE, exist_ok=True)
        self._path = os.path.join(_BASE, f"{name}.sqlite")
        self._lock = threading.Lock()
        with self._conn() as conn:
            conn.execute("CREATE TABLE IF NOT EXISTS kv (k TEXT PRIMARY KEY, v TEXT)")

    def _conn(self) -> sqlite3.Connection:
        return sqlite3.connect(self._path, timeout=30)

    @staticmethod
    def key(*parts: str) -> str:
        return hashlib.sha256("||".join(parts).encode()).hexdigest()

    def get(self, key: str) -> Optional[Any]:
        with self._lock, self._conn() as conn:
            row = conn.execute("SELECT v FROM kv WHERE k = ?", (key,)).fetchone()
        return json.loads(row[0]) if row else None

    def set(self, key: str, value: Any) -> None:
        with self._lock, self._conn() as conn:
            conn.execute(
                "INSERT OR REPLACE INTO kv (k, v) VALUES (?, ?)", (key, json.dumps(value))
            )

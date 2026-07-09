"""Lexicon meta key/value (phoneme vocab fingerprint — ADR-0037)."""
from __future__ import annotations

import sqlite3
from pathlib import Path

from app.domain.lexicon.phoneme_codec import PHONEME_VOCAB_VERSION, phoneme_vocab_fingerprint

META_TABLE_SQL = """
CREATE TABLE IF NOT EXISTS lexicon_meta (
  key TEXT PRIMARY KEY NOT NULL,
  value TEXT NOT NULL
)
"""

KEY_PHONEME_VOCAB_VERSION = "phoneme_vocab_version"
KEY_PHONEME_VOCAB_FP = "phoneme_vocab_fingerprint"


def ensure_lexicon_meta_table(conn: sqlite3.Connection) -> None:
    conn.execute(META_TABLE_SQL)


def write_phoneme_vocab_meta(db_path: Path | str) -> None:
    path = Path(db_path)
    fp = phoneme_vocab_fingerprint()
    with sqlite3.connect(path) as conn:
        ensure_lexicon_meta_table(conn)
        conn.execute(
            "INSERT OR REPLACE INTO lexicon_meta(key, value) VALUES (?, ?)",
            (KEY_PHONEME_VOCAB_VERSION, PHONEME_VOCAB_VERSION),
        )
        conn.execute(
            "INSERT OR REPLACE INTO lexicon_meta(key, value) VALUES (?, ?)",
            (KEY_PHONEME_VOCAB_FP, fp),
        )
        conn.commit()


def read_phoneme_vocab_meta(db_path: Path | str) -> dict[str, str]:
    path = Path(db_path)
    out: dict[str, str] = {}
    with sqlite3.connect(path) as conn:
        try:
            rows = conn.execute(
                "SELECT key, value FROM lexicon_meta WHERE key IN (?, ?)",
                (KEY_PHONEME_VOCAB_VERSION, KEY_PHONEME_VOCAB_FP),
            ).fetchall()
        except sqlite3.OperationalError:
            return out
        for k, v in rows:
            out[str(k)] = str(v)
    return out


def phoneme_vocab_meta_ok(db_path: Path | str) -> bool:
    meta = read_phoneme_vocab_meta(db_path)
    return (
        meta.get(KEY_PHONEME_VOCAB_VERSION) == PHONEME_VOCAB_VERSION
        and meta.get(KEY_PHONEME_VOCAB_FP) == phoneme_vocab_fingerprint()
    )


__all__ = [
    "KEY_PHONEME_VOCAB_FP",
    "KEY_PHONEME_VOCAB_VERSION",
    "ensure_lexicon_meta_table",
    "phoneme_vocab_meta_ok",
    "read_phoneme_vocab_meta",
    "write_phoneme_vocab_meta",
]

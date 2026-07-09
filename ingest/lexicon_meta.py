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


def samples_legacy_json_phoneme(db_path: Path | str, *, limit: int = 20) -> bool:
    """True if any sampled initials/finals still look like JSON arrays (pre-J2)."""
    path = Path(db_path)
    with sqlite3.connect(path) as conn:
        try:
            rows = conn.execute(
                "SELECT finals, initials FROM words "
                "WHERE (finals IS NOT NULL AND finals != '') "
                "   OR (initials IS NOT NULL AND initials != '') "
                "LIMIT ?",
                (limit,),
            ).fetchall()
        except sqlite3.OperationalError:
            return False
    for fin, ini in rows:
        for raw in (fin, ini):
            if isinstance(raw, str) and raw.strip().startswith("["):
                return True
    return False


def phoneme_storage_contract_ok(db_path: Path | str) -> bool:
    """Meta fingerprint matches and no legacy JSON samples."""
    if not Path(db_path).is_file():
        return False
    if samples_legacy_json_phoneme(db_path):
        return False
    return phoneme_vocab_meta_ok(db_path)


def ensure_phoneme_storage_contract(
    db_path: Path | str,
    *,
    allow_migrate: bool = True,
) -> str:
    """
    C1: ensure compact phoneme storage (ADR-0037/0038).
    Returns status: 'ok' | 'migrated'.
    Raises RuntimeError if unfixable without migrate or migrate fails.
    """
    path = Path(db_path)
    if not path.is_file():
        raise RuntimeError(f"lyrics.db missing: {path}")
    if phoneme_storage_contract_ok(path):
        return "ok"
    if not allow_migrate:
        raise RuntimeError(
            "詞庫音素欄位契約不符（要 j2 compact + lexicon_meta 指紋）。"
            f" 請執行: python -m ingest.migrate_phoneme_compact {path}"
        )
    from ingest.migrate_phoneme_compact import migrate_db

    try:
        migrate_db(path, vacuum=False)
    except Exception as exc:
        raise RuntimeError(
            f"音素欄位自動遷移失敗: {exc}. "
            f"請手動: python -m ingest.migrate_phoneme_compact {path}"
        ) from exc
    if not phoneme_storage_contract_ok(path):
        raise RuntimeError(
            "遷移後仍未通過音素契約。"
            f" 請手動: python -m ingest.migrate_phoneme_compact {path}"
        )
    return "migrated"


__all__ = [
    "KEY_PHONEME_VOCAB_FP",
    "KEY_PHONEME_VOCAB_VERSION",
    "ensure_lexicon_meta_table",
    "ensure_phoneme_storage_contract",
    "phoneme_storage_contract_ok",
    "phoneme_vocab_meta_ok",
    "read_phoneme_vocab_meta",
    "samples_legacy_json_phoneme",
    "write_phoneme_vocab_meta",
]

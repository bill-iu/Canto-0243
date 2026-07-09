"""Lexicon SQLite index allowlist — ADR v1.0.7 I2."""
from __future__ import annotations

import sqlite3
from pathlib import Path

# Tier 1 duplicates + Tier 2/3 unused single-column indexes (EXPLAIN-audited).
FORBIDDEN_LEXICON_INDEXES = frozenset(
    {
        "idx_length_code",
        "idx_length_code_finals_model",
        "idx_words_length",
        "ix_words_length",
        "ix_words_code",
        "ix_words_finals",
        "ix_words_initials",
        "ix_word_relations_word_id",
        "ix_word_relations_related_id",
        "ix_word_relations_relation_type",
        # ADR-0038 U1: explicit UNIQUE duplicates table CONSTRAINT autoindex
        "uq_word_relation",
    }
)

REQUIRED_LEXICON_INDEXES = frozenset(
    {
        "ix_words_char",
        "idx_length_code_finals",
        "idx_word_rel_word_type",
        "idx_word_rel_related_type",
    }
)


def list_user_indexes(db_path: Path | str) -> set[str]:
    with sqlite3.connect(db_path) as conn:
        rows = conn.execute(
            "SELECT name FROM sqlite_master WHERE type='index' AND name NOT LIKE 'sqlite_%'"
        ).fetchall()
    return {str(r[0]) for r in rows}


def _has_word_relations_table_unique_constraint(conn: sqlite3.Connection) -> bool:
    """True when CREATE TABLE embeds UNIQUE(word_id, related_id, relation_type) (autoindex)."""
    row = conn.execute(
        "SELECT sql FROM sqlite_master WHERE type='table' AND name='word_relations'"
    ).fetchone()
    if not row or not row[0]:
        return False
    sql = str(row[0]).upper()
    return "UNIQUE" in sql and "WORD_ID" in sql and "RELATED_ID" in sql


def finalize_lexicon_indexes(db_path: Path | str) -> list[str]:
    """Drop forbidden indexes; return names dropped."""
    dropped: list[str] = []
    with sqlite3.connect(db_path) as conn:
        rows = conn.execute(
            "SELECT name FROM sqlite_master WHERE type='index' AND name NOT LIKE 'sqlite_%'"
        ).fetchall()
        existing = {str(r[0]) for r in rows}
        forbid = set(FORBIDDEN_LEXICON_INDEXES)
        # Only drop explicit uq when table CONSTRAINT already enforces uniqueness
        if "uq_word_relation" in existing and not _has_word_relations_table_unique_constraint(conn):
            forbid.discard("uq_word_relation")
        for name in sorted(forbid & existing):
            conn.execute(f'DROP INDEX IF EXISTS "{name}"')
            dropped.append(name)
        conn.commit()
    return dropped


__all__ = [
    "FORBIDDEN_LEXICON_INDEXES",
    "REQUIRED_LEXICON_INDEXES",
    "finalize_lexicon_indexes",
    "list_user_indexes",
]
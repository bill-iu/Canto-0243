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


def finalize_lexicon_indexes(db_path: Path | str) -> list[str]:
    """Drop forbidden indexes; return names dropped."""
    dropped: list[str] = []
    with sqlite3.connect(db_path) as conn:
        rows = conn.execute(
            "SELECT name FROM sqlite_master WHERE type='index' AND name NOT LIKE 'sqlite_%'"
        ).fetchall()
        existing = {str(r[0]) for r in rows}
        for name in sorted(FORBIDDEN_LEXICON_INDEXES & existing):
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
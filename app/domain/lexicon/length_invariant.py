"""Validate or repair the lexicon word-length invariant."""

from __future__ import annotations

import sqlite3
from contextlib import closing
from pathlib import Path


_INVALID_LENGTH = "length IS NULL OR length = 0 OR length != length(char)"


class LexiconLengthInvariantError(RuntimeError):
    def __init__(self, invalid_rows: int) -> None:
        self.invalid_rows = invalid_rows
        super().__init__(f"lexicon has {invalid_rows} invalid words.length rows")


def _invalid_count(conn: sqlite3.Connection) -> int:
    return int(
        conn.execute(f"SELECT COUNT(*) FROM words WHERE {_INVALID_LENGTH}").fetchone()[0]
    )


def assert_lexicon_length_invariant(db_path: Path | str) -> None:
    """Reject a lexicon unless every words.length value is present and correct."""
    with closing(sqlite3.connect(db_path)) as conn, conn:
        invalid = _invalid_count(conn)
        if invalid:
            raise LexiconLengthInvariantError(invalid)


def repair_legacy_lexicon_lengths(db_path: Path | str) -> int:
    """Repair a local legacy lexicon atomically, then verify the invariant."""
    with closing(sqlite3.connect(db_path)) as conn, conn:
        invalid = _invalid_count(conn)
        if not invalid:
            return 0
        conn.execute(
            f"UPDATE words SET length = length(char) WHERE {_INVALID_LENGTH}"
        )
        remaining = _invalid_count(conn)
        if remaining:
            raise LexiconLengthInvariantError(remaining)
        return invalid


__all__ = [
    "LexiconLengthInvariantError",
    "assert_lexicon_length_invariant",
    "repair_legacy_lexicon_lengths",
]

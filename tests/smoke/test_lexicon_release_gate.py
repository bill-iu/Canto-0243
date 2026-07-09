"""詞庫發佈閘 tests (T4)."""
from __future__ import annotations

import sqlite3
import tempfile
import unittest
from pathlib import Path

from ingest.lexicon_release_gate import check_lexicon_release_gate


def _tiny_db(path: Path, *, phrase_rows: int, pad_mb: float = 0) -> None:
    with sqlite3.connect(path) as conn:
        conn.execute("CREATE TABLE words (id INTEGER PRIMARY KEY, source_flags INTEGER)")
        for i in range(phrase_rows):
            conn.execute("INSERT INTO words(source_flags) VALUES (8)")
        conn.execute("CREATE INDEX ix_words_char ON words(id)")
        if pad_mb > 0:
            blob = b"x" * int(pad_mb * 1024 * 1024)
            conn.execute("CREATE TABLE pad (b BLOB)")
            conn.execute("INSERT INTO pad VALUES (?)", (blob,))
        conn.commit()


class LexiconReleaseGateTests(unittest.TestCase):
    def test_small_fixture_passes_phrase_ratio_when_low_rows(self):
        with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as fh:
            path = Path(fh.name)
        try:
            _tiny_db(path, phrase_rows=100_000)
            result = check_lexicon_release_gate(path)
            self.assertTrue(result.ok, result.messages)
        finally:
            try:
                path.unlink(missing_ok=True)
            except PermissionError:
                pass

    def test_fails_when_db_over_cap(self):
        with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as fh:
            path = Path(fh.name)
        try:
            _tiny_db(path, phrase_rows=10, pad_mb=96)
            result = check_lexicon_release_gate(path)
            self.assertFalse(result.ok)
            self.assertTrue(any("db" in m and "MB" in m for m in result.messages))
        finally:
            try:
                path.unlink(missing_ok=True)
            except PermissionError:
                pass


if __name__ == "__main__":
    unittest.main()
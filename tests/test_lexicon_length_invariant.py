from __future__ import annotations

import sqlite3
import tempfile
import unittest
from contextlib import closing
from pathlib import Path

from app.domain.lexicon.length_invariant import (
    LexiconLengthInvariantError,
    assert_lexicon_length_invariant,
    repair_legacy_lexicon_lengths,
)


class LexiconLengthInvariantTests(unittest.TestCase):
    def setUp(self) -> None:
        handle = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
        handle.close()
        self.db_path = Path(handle.name)
        with closing(sqlite3.connect(self.db_path)) as conn, conn:
            conn.execute(
                "CREATE TABLE words (id INTEGER PRIMARY KEY, char TEXT, length INTEGER)"
            )
            conn.executemany(
                "INSERT INTO words(char, length) VALUES (?, ?)",
                [("香", 1), ("香港", None), ("廣東話", 2)],
            )

    def tearDown(self) -> None:
        self.db_path.unlink(missing_ok=True)

    def test_strict_open_rejects_incomplete_or_incorrect_lengths(self) -> None:
        with self.assertRaises(LexiconLengthInvariantError) as caught:
            assert_lexicon_length_invariant(self.db_path)

        self.assertEqual(caught.exception.invalid_rows, 2)
        with closing(sqlite3.connect(self.db_path)) as conn:
            self.assertEqual(
                conn.execute("SELECT length FROM words ORDER BY id").fetchall(),
                [(1,), (None,), (2,)],
            )

    def test_local_repair_is_complete_before_strict_open_succeeds(self) -> None:
        repaired = repair_legacy_lexicon_lengths(self.db_path)

        self.assertEqual(repaired, 2)
        self.assertIsNone(assert_lexicon_length_invariant(self.db_path))
        with closing(sqlite3.connect(self.db_path)) as conn:
            self.assertEqual(
                conn.execute("SELECT length FROM words ORDER BY id").fetchall(),
                [(1,), (2,), (3,)],
            )


if __name__ == "__main__":
    unittest.main()

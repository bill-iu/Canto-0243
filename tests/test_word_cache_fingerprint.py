"""磁碟快取指紋 — 內容綁定（唔綁路徑）。"""
from __future__ import annotations

import os
import shutil
import tempfile
import unittest
from pathlib import Path

from app.utils.word_cache import (
    complete_preload,
    persist_word_cache_to_disk,
    populate_word_cache_from_rows,
    reset_word_cache_for_tests,
    try_restore_word_cache_from_disk,
)


class WordCacheFingerprintTests(unittest.TestCase):
    def setUp(self):
        reset_word_cache_for_tests()
        self._prev = os.environ.get("WORD_CACHE_DISK")
        os.environ["WORD_CACHE_DISK"] = "1"

    def tearDown(self):
        reset_word_cache_for_tests()
        if self._prev is None:
            os.environ.pop("WORD_CACHE_DISK", None)
        else:
            os.environ["WORD_CACHE_DISK"] = self._prev

    def test_restore_after_copy_to_different_path(self):
        rows = [
            {
                "char": "做就",
                "code": "23",
                "jyutping": "zou6 zau6",
                "finals": '["ou","au"]',
                "initials": '["z","z"]',
                "length": 2,
            }
        ]
        with tempfile.TemporaryDirectory() as tmp_a, tempfile.TemporaryDirectory() as tmp_b:
            db_a = Path(tmp_a) / "lyrics.db"
            db_b = Path(tmp_b) / "lyrics.db"
            db_a.write_bytes(b"sqlite-placeholder")
            shutil.copy2(db_a, db_b)

            populate_word_cache_from_rows(rows)
            complete_preload()
            persist_word_cache_to_disk(db_path=db_a, cache_dir=Path(tmp_a) / ".cache")
            shutil.copytree(Path(tmp_a) / ".cache", Path(tmp_b) / ".cache")

            reset_word_cache_for_tests()
            self.assertTrue(
                try_restore_word_cache_from_disk(
                    db_path=db_b,
                    cache_dir=Path(tmp_b) / ".cache",
                )
            )


if __name__ == "__main__":
    unittest.main()

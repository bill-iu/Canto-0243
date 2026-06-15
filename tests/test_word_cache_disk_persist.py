"""Disk-backed word_cache snapshot (optional cold-start acceleration)."""
from __future__ import annotations

import os
import unittest

from app.utils.word_cache import (
    _disk_cache_path,
    complete_preload,
    get_word_cache_stats,
    persist_word_cache_to_disk,
    populate_word_cache_from_rows,
    reset_word_cache_for_tests,
    try_restore_word_cache_from_disk,
)


class WordCacheDiskPersistTests(unittest.TestCase):
    def setUp(self):
        reset_word_cache_for_tests()
        self._prev = os.environ.get("WORD_CACHE_DISK")
        os.environ["WORD_CACHE_DISK"] = "1"
        path = _disk_cache_path()
        if path.is_file():
            path.unlink()

    def tearDown(self):
        reset_word_cache_for_tests()
        path = _disk_cache_path()
        if path.is_file():
            path.unlink()
        if self._prev is None:
            os.environ.pop("WORD_CACHE_DISK", None)
        else:
            os.environ["WORD_CACHE_DISK"] = self._prev

    def test_persist_and_restore_roundtrip(self):
        rows = [
            {
                "char": "香港",
                "code": "33",
                "jyutping": "hoeng1 gong2",
                "finals": '["oeng","ong"]',
                "initials": '["h","g"]',
                "length": 2,
            }
        ]
        populate_word_cache_from_rows(rows)
        complete_preload()
        before = get_word_cache_stats()["total_entries"]
        persist_word_cache_to_disk()
        reset_word_cache_for_tests()
        self.assertTrue(try_restore_word_cache_from_disk())
        after = get_word_cache_stats()["total_entries"]
        self.assertEqual(before, after)


if __name__ == "__main__":
    unittest.main()

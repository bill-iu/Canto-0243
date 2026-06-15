"""詞庫快取索引模組拆分 — facade 與子模組行為一致。"""
from __future__ import annotations

import unittest

from app.utils import word_cache_disk as disk
from app.utils import word_cache_index as index
from app.utils import word_cache_preload as preload
from app.utils.word_cache import (
    get_word_cache_stats,
    is_word_cache_ready,
    populate_word_cache_from_rows,
    reset_word_cache_for_tests,
    try_restore_word_cache_from_disk,
)


class WordCacheIndexSplitTests(unittest.TestCase):
    def setUp(self):
        reset_word_cache_for_tests()

    def tearDown(self):
        reset_word_cache_for_tests()

    def test_populate_via_facade_matches_index_stats(self):
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
        self.assertEqual(get_word_cache_stats(), index.get_stats())
        self.assertTrue(index.is_populated())

    def test_preload_adapter_owns_lifecycle_not_index(self):
        preload.begin_preload()
        self.assertEqual(preload.get_preload_snapshot()["status"], "loading")
        self.assertFalse(index.is_populated())
        index.populate_from_rows(
            [
                {
                    "char": "港",
                    "code": "3",
                    "jyutping": "gong2",
                    "finals": '["ong"]',
                    "initials": '["g"]',
                    "length": 1,
                }
            ]
        )
        preload.complete_preload()
        self.assertTrue(is_word_cache_ready())

    def test_disk_roundtrip_via_facade(self):
        import os

        prev = os.environ.get("WORD_CACHE_DISK")
        os.environ["WORD_CACHE_DISK"] = "1"
        path = disk.disk_cache_path()
        if path.is_file():
            path.unlink()
        try:
            populate_word_cache_from_rows(
                [
                    {
                        "char": "港",
                        "code": "3",
                        "jyutping": "gong2",
                        "finals": '["ong"]',
                        "initials": '["g"]',
                        "length": 1,
                    }
                ]
            )
            preload.complete_preload()
            from app.utils.word_cache import persist_word_cache_to_disk

            persist_word_cache_to_disk()
            reset_word_cache_for_tests()
            self.assertTrue(try_restore_word_cache_from_disk())
            self.assertTrue(index.is_populated())
        finally:
            if path.is_file():
                path.unlink()
            if prev is None:
                os.environ.pop("WORD_CACHE_DISK", None)
            else:
                os.environ["WORD_CACHE_DISK"] = prev


if __name__ == "__main__":
    unittest.main()

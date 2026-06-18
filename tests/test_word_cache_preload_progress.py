"""就緒閘進度：populate 細分回報；/ready 提供 word_cache_progress 與 tail_progress。"""
from __future__ import annotations

import unittest

from app.startup.offline_preload import get_readiness_snapshot, reset_background_preload_state_for_tests
from app.utils.word_cache import (
    begin_preload,
    populate_word_cache_from_rows,
    reset_word_cache_for_tests,
)


class WordCachePreloadProgressTests(unittest.TestCase):
    def setUp(self):
        reset_word_cache_for_tests()
        reset_background_preload_state_for_tests()

    def tearDown(self):
        reset_word_cache_for_tests()
        reset_background_preload_state_for_tests()

    def test_populate_reports_granular_progress_while_loading(self):
        begin_preload()
        rows = [
            {
                "char": f"字{i}",
                "code": "1",
                "jyutping": "zi6",
                "finals": '["i"]',
                "initials": '["z"]',
                "length": 2,
            }
            for i in range(5000)
        ]
        populate_word_cache_from_rows(rows)
        from app.utils.word_cache import get_preload_snapshot

        snap = get_preload_snapshot()
        self.assertEqual(snap["status"], "loading")
        self.assertGreater(snap["progress"], 0.55)

    def test_readiness_exposes_word_cache_and_tail_progress(self):
        from app.startup import offline_preload as mod

        mod._set_background_phase("static_resources", status="ready", progress=1.0)
        mod._set_background_phase("compound_syn", status="loading", progress=0.05)
        mod._set_background_phase("compound_ant", status="pending", progress=0.0)
        begin_preload()
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
        from app.utils.word_cache import complete_preload

        complete_preload()
        payload = get_readiness_snapshot()
        self.assertAlmostEqual(payload["word_cache_progress"], 1.0)
        self.assertAlmostEqual(payload["tail_progress"], 0.35, places=2)
        self.assertGreater(payload["progress"], payload["word_cache_progress"] * 0.3)


if __name__ == "__main__":
    unittest.main()

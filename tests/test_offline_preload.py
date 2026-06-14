"""離線啟動預載模組測試。"""
from __future__ import annotations

import unittest
from unittest.mock import patch

from app.startup.offline_preload import (
    get_readiness_snapshot,
    preload_static_runtime_resources,
    run_lifespan_startup,
    run_main_block_startup,
)
from app.utils.word_cache import complete_preload, populate_word_cache_from_rows, reset_word_cache_for_tests


class OfflinePreloadTests(unittest.TestCase):
    def setUp(self):
        reset_word_cache_for_tests()

    def tearDown(self):
        reset_word_cache_for_tests()

    def test_get_readiness_snapshot_reflects_word_cache(self):
        payload = get_readiness_snapshot()
        self.assertFalse(payload["ready"])
        populate_word_cache_from_rows(
            [
                {
                    "char": "做就",
                    "code": "23",
                    "jyutping": "zou6 zau6",
                    "finals": '["ou","au"]',
                    "initials": '["z","z"]',
                    "length": 2,
                }
            ]
        )
        complete_preload()
        payload = get_readiness_snapshot()
        self.assertTrue(payload["ready"])

    @patch("app.startup.offline_preload.start_background_word_cache_preload")
    @patch("app.startup.offline_preload.ensure_dev_length_schema")
    def test_run_lifespan_startup_triggers_word_cache(self, _schema, word_cache):
        run_lifespan_startup(env="local")
        word_cache.assert_called_once()

    @patch("app.startup.offline_preload.preload_compound_syn_runtime_cache")
    @patch("app.startup.offline_preload.preload_static_runtime_resources")
    @patch("app.startup.offline_preload.run_local_db_bootstrap")
    @patch("app.startup.offline_preload.run_create_all_if_needed")
    def test_run_main_block_startup_orchestrates_eager_preload(
        self, create_all, bootstrap, static_resources, compound_cache
    ):
        run_main_block_startup(env="local")
        create_all.assert_called_once_with("local")
        bootstrap.assert_called_once_with("local")
        static_resources.assert_called_once_with()
        compound_cache.assert_called_once_with()

    @patch("app.startup.offline_preload._best_effort")
    def test_preload_static_runtime_resources_calls_all_loaders(self, best_effort):
        preload_static_runtime_resources()
        self.assertEqual(best_effort.call_count, 5)


if __name__ == "__main__":
    unittest.main()

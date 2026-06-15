"""離線啟動預載模組測試。"""
from __future__ import annotations

import unittest
from unittest.mock import patch

from app.startup.offline_preload import (
    get_readiness_snapshot,
    preload_static_runtime_resources,
    reset_background_preload_state_for_tests,
    run_lifespan_startup,
    run_main_block_startup,
)
from app.utils.word_cache import complete_preload, populate_word_cache_from_rows, reset_word_cache_for_tests


class OfflinePreloadTests(unittest.TestCase):
    def setUp(self):
        reset_word_cache_for_tests()
        reset_background_preload_state_for_tests()

    def tearDown(self):
        reset_word_cache_for_tests()
        reset_background_preload_state_for_tests()

    def test_get_readiness_snapshot_reflects_word_cache(self):
        payload = get_readiness_snapshot()
        self.assertFalse(payload["ready"])
        self.assertFalse(payload["startup_complete"])
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
        self.assertFalse(payload["startup_complete"])

    def test_gate_ready_when_word_cache_phase_done_without_buckets(self):
        from app.startup import offline_preload as mod

        complete_preload()
        mod._set_background_phase("static_resources", status="ready", progress=1.0)
        mod._set_background_phase("compound_syn", status="ready", progress=1.0)
        payload = get_readiness_snapshot()
        self.assertFalse(payload["ready"])
        self.assertTrue(payload["gate_ready"])
        self.assertFalse(payload["startup_complete"])

    def test_startup_complete_when_all_background_phases_done(self):
        from app.startup import offline_preload as mod

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
        mod._set_background_phase("static_resources", status="ready", progress=1.0)
        mod._set_background_phase("compound_syn", status="ready", progress=1.0)

        payload = get_readiness_snapshot()
        self.assertTrue(payload["startup_complete"])
        self.assertFalse(payload["tail_pending"])

    @patch("app.startup.offline_preload.start_background_runtime_preload")
    @patch("app.startup.offline_preload.ensure_dev_length_schema")
    @patch("app.startup.offline_preload.run_local_db_bootstrap")
    @patch("app.startup.offline_preload.run_create_all_if_needed")
    def test_run_lifespan_startup_triggers_background_preload(
        self, create_all, bootstrap, _schema, background
    ):
        run_lifespan_startup(env="local")
        create_all.assert_called_once_with("local")
        bootstrap.assert_called_once_with("local")
        background.assert_called_once()

    @patch("app.startup.offline_preload.preload_compound_syn_runtime_cache")
    @patch("app.startup.offline_preload.preload_static_runtime_resources")
    @patch("app.startup.offline_preload.run_local_db_bootstrap")
    @patch("app.startup.offline_preload.run_create_all_if_needed")
    def test_run_main_block_startup_only_db_bootstrap(
        self, create_all, bootstrap, static_resources, compound_cache
    ):
        run_main_block_startup(env="local")
        create_all.assert_called_once_with("local")
        bootstrap.assert_called_once_with("local")
        static_resources.assert_not_called()
        compound_cache.assert_not_called()

    @patch("app.startup.offline_preload._best_effort")
    def test_preload_static_runtime_resources_calls_all_loaders(self, best_effort):
        preload_static_runtime_resources()
        self.assertEqual(best_effort.call_count, 5)


if __name__ == "__main__":
    unittest.main()

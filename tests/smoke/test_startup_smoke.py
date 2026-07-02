"""啟動／就緒閘／word_cache smoke。"""
from __future__ import annotations

import os
import shutil
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from app.startup.offline_preload import reset_background_preload_state_for_tests
from app.startup.readiness_gate import (
    SearchGateBlocked,
    require_search_ready,
    reset_readiness_gate_for_tests,
    snapshot,
)
from app.utils.word_cache import (
    complete_preload,
    persist_word_cache_to_disk,
    populate_word_cache_from_rows,
    reset_word_cache_for_tests,
    try_restore_word_cache_from_disk,
)


class StartupSmokeTests(unittest.TestCase):
    def setUp(self):
        os.environ["READINESS_GATE_ENFORCE"] = "1"
        reset_word_cache_for_tests()
        reset_background_preload_state_for_tests()
        reset_readiness_gate_for_tests()

    def tearDown(self):
        os.environ.pop("READINESS_GATE_ENFORCE", None)
        reset_word_cache_for_tests()
        reset_background_preload_state_for_tests()
        reset_readiness_gate_for_tests()

    def test_snapshot_opens_on_ready(self):
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
        payload = snapshot()
        self.assertTrue(payload["gate_ready"])
        self.assertTrue(payload["ready"])
        self.assertEqual(payload["gate_open_reason"], "ready")

    def test_require_search_ready_gate(self):
        with self.assertRaises(SearchGateBlocked):
            require_search_ready()
        complete_preload()
        require_search_ready()

    def test_compound_ant_failed_still_startup_complete(self):
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
        mod._set_background_phase("compound_ant", status="failed", progress=1.0, error="boom")
        payload = snapshot()
        self.assertTrue(payload["startup_complete"])
        self.assertFalse(payload["tail_pending"])

    def test_word_cache_restore_after_copy_to_different_path(self):
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
        prev = os.environ.get("WORD_CACHE_DISK")
        os.environ["WORD_CACHE_DISK"] = "1"
        try:
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
        finally:
            if prev is None:
                os.environ.pop("WORD_CACHE_DISK", None)
            else:
                os.environ["WORD_CACHE_DISK"] = prev


if __name__ == "__main__":
    unittest.main()

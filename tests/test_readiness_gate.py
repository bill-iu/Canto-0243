"""就緒閘 policy — server 契約（ADR-0001）。"""
from __future__ import annotations

import os
import unittest
from unittest.mock import patch

from app.startup.offline_preload import reset_background_preload_state_for_tests
from app.startup.readiness_gate import (
    DEFAULT_DEGRADE_MS,
    SearchGateBlocked,
    require_search_ready,
    reset_readiness_gate_for_tests,
    snapshot,
)
from app.utils.word_cache import (
    begin_preload,
    complete_preload,
    fail_preload,
    populate_word_cache_from_rows,
    reset_word_cache_for_tests,
)


class ReadinessGatePolicyTests(unittest.TestCase):
    def setUp(self):
        os.environ["READINESS_GATE_ENFORCE"] = "1"
        reset_word_cache_for_tests()
        reset_background_preload_state_for_tests()
        reset_readiness_gate_for_tests()

    def tearDown(self):
        os.environ.pop("READINESS_GATE_ENFORCE", None)
        os.environ.pop("GATE_DEGRADE_MS", None)
        reset_word_cache_for_tests()
        reset_background_preload_state_for_tests()
        reset_readiness_gate_for_tests()

    def test_snapshot_locked_while_word_cache_pending(self):
        payload = snapshot()
        self.assertFalse(payload["gate_ready"])
        self.assertFalse(payload["degraded"])
        self.assertIsNone(payload["gate_open_reason"])

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
        self.assertFalse(payload["degraded"])

    def test_snapshot_opens_on_failed(self):
        begin_preload()
        fail_preload("disk error")
        payload = snapshot()
        self.assertTrue(payload["gate_ready"])
        self.assertEqual(payload["gate_open_reason"], "failed")
        self.assertFalse(payload["ready"])

    def test_snapshot_opens_on_degraded_after_timeout(self):
        begin_preload()
        t0 = 1000.0
        with patch("app.startup.readiness_gate.time.monotonic", side_effect=[t0, t0, t0 + 31]):
            snap1 = snapshot()
            self.assertFalse(snap1["gate_ready"])
            snap2 = snapshot()
            self.assertTrue(snap2["gate_ready"])
            self.assertTrue(snap2["degraded"])
            self.assertEqual(snap2["gate_open_reason"], "degraded")

    def test_require_search_ready_raises_when_locked(self):
        with self.assertRaises(SearchGateBlocked) as ctx:
            require_search_ready()
        self.assertFalse(ctx.exception.snapshot["gate_ready"])

    def test_require_search_ready_passes_when_open(self):
        complete_preload()
        require_search_ready()

    def test_degrade_timeout_respects_env(self):
        os.environ["GATE_DEGRADE_MS"] = "500"
        begin_preload()
        t0 = 2000.0
        with patch("app.startup.readiness_gate.time.monotonic", side_effect=[t0, t0, t0 + 0.6]):
            self.assertFalse(snapshot()["gate_ready"])
            opened = snapshot()
            self.assertTrue(opened["gate_ready"])
            self.assertEqual(opened["gate_open_reason"], "degraded")

    def test_default_degrade_ms_is_30_seconds(self):
        self.assertEqual(DEFAULT_DEGRADE_MS, 30_000)


if __name__ == "__main__":
    unittest.main()

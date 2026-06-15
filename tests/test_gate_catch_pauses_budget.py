"""Regression: catch 分支必須暫停 gate budget（對應 frontend waitForPreloadReady）。"""
from __future__ import annotations

import unittest

from tests.test_gate_budget import PRELOAD_TIMEOUT_MS, POLL_MS, _can_open, simulate_polls


class GateCatchPausesBudgetTests(unittest.TestCase):
    def test_failures_after_loading_do_not_deplete_budget_before_ready(self):
        """若 catch 唔 pause budget，25s 斷線會喺恢復前耗盡 30s。"""
        loading = {
            "ready": False,
            "status": "loading",
            "progress": 0.53,
            "phases": {"word_cache": {"status": "loading"}},
        }
        ready = {
            "ready": True,
            "status": "ready",
            "progress": 1.0,
            "phases": {"word_cache": {"status": "ready"}},
        }
        fail_polls = int(25_000 / POLL_MS)
        events = [("ok", loading)] * 3 + [("fail", None)] * fail_polls + [("ok", ready)]
        self.assertEqual(simulate_polls(events), "success")


if __name__ == "__main__":
    unittest.main()

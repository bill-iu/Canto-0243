"""就緒閘逾時：連線失敗暫停 budget（B 方案）。"""
from __future__ import annotations

import unittest

PRELOAD_TIMEOUT_MS = 30_000
POLL_MS = 220


def _can_open(data: dict) -> bool:
    if data.get("ready") or data.get("gate_ready"):
        return True
    wc = (data.get("phases") or {}).get("word_cache") or {}
    return wc.get("status") in ("ready", "failed")


def simulate_polls(events: list[tuple[str, dict | None]]) -> str:
    clock = 0
    budget_ms = PRELOAD_TIMEOUT_MS
    budget_active = False
    budget_last_at = 0

    def pause_budget() -> None:
        nonlocal budget_active, budget_ms, budget_last_at
        if budget_active:
            budget_ms -= clock - budget_last_at
            budget_active = False

    def resume_budget() -> None:
        nonlocal budget_active, budget_last_at
        if not budget_active:
            budget_active = True
            budget_last_at = clock

    for kind, payload in events:
        clock += POLL_MS
        if kind == "ok":
            pause_budget()
            assert payload is not None
            resume_budget()
            if _can_open(payload):
                return "success"
            budget_ms -= clock - budget_last_at
            budget_last_at = clock
            if budget_ms <= 0:
                return "degraded"
        else:
            pause_budget()
    return "incomplete"


class GateBudgetTests(unittest.TestCase):
    def test_failures_before_first_ok_do_not_degrade(self):
        loading = {
            "ready": False,
            "status": "loading",
            "progress": 0.08,
            "phases": {"word_cache": {"status": "loading"}},
        }
        ready = {
            "ready": True,
            "status": "ready",
            "progress": 1.0,
            "phases": {"word_cache": {"status": "ready"}},
        }
        events = [("fail", None)] * 10 + [("ok", loading)] * 5 + [("ok", ready)]
        self.assertEqual(simulate_polls(events), "success")

    def test_fail_streak_mid_preload_does_not_consume_budget(self):
        loading = {
            "ready": False,
            "status": "loading",
            "progress": 0.4,
            "phases": {"word_cache": {"status": "loading"}},
        }
        ready = {
            "ready": True,
            "status": "ready",
            "progress": 1.0,
            "phases": {"word_cache": {"status": "ready"}},
        }
        events = [("ok", loading)] * 23 + [("fail", None)] * 114 + [("ok", ready)]
        self.assertEqual(simulate_polls(events), "success")

    def test_loading_over_budget_degrades(self):
        loading = {
            "ready": False,
            "status": "loading",
            "progress": 0.4,
            "phases": {"word_cache": {"status": "loading"}},
        }
        polls_needed = PRELOAD_TIMEOUT_MS // POLL_MS + 2
        events = [("ok", loading)] * polls_needed
        self.assertEqual(simulate_polls(events), "degraded")


if __name__ == "__main__":
    unittest.main()

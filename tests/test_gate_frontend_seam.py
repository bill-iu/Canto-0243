"""接縫測試：前端就緒閘不得保留第二份 gate policy。"""
from __future__ import annotations

import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
INDEX_PATH = REPO_ROOT / "frontend" / "index.html"
GATE_MJS_PATH = REPO_ROOT / "frontend" / "gate.mjs"
SEARCH_MJS_PATH = REPO_ROOT / "frontend" / "search-workbench.mjs"

FORBIDDEN = (
    "canOpenSearchGate",
    "PRELOAD_TIMEOUT",
    "budget_ms",
    "budget_active",
    "pauseBudget",
    "resumeBudget",
    "data.ready ||",
)

REQUIRED = (
    "data.gate_ready",
    "data.degraded",
    "formatGateStatusLabel",
    'fetch("/ready"',
    "仲未開得工",
)


class TestGateFrontendSeam(unittest.TestCase):
    def test_index_html_has_no_client_gate_policy(self):
        source = INDEX_PATH.read_text(encoding="utf-8")
        for symbol in FORBIDDEN:
            with self.subTest(symbol=symbol):
                self.assertNotIn(symbol, source)

    def test_index_html_uses_server_gate_contract(self):
        gate = GATE_MJS_PATH.read_text(encoding="utf-8")
        search = SEARCH_MJS_PATH.read_text(encoding="utf-8")
        bundle = gate + search
        for symbol in REQUIRED:
            with self.subTest(symbol=symbol):
                self.assertIn(symbol, bundle)
        self.assertIn('src="./main.mjs"', INDEX_PATH.read_text(encoding="utf-8"))


if __name__ == "__main__":
    unittest.main()

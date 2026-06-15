"""接縫測試：近義複合候選規則僅在近義複合模組定義。"""
from __future__ import annotations

import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
EXECUTOR_PATH = REPO_ROOT / "app" / "services" / "compound_syn_executor.py"
PRELOAD_PATH = REPO_ROOT / "app" / "startup" / "offline_preload.py"

EXECUTOR_FORBIDDEN = (
    "load_compound_synonyms",
    "_scan_morpheme_compounds",
    "synthesize_compound_literals",
    "build_compound_syn_snapshot",
    "ensure_compound_syn_snapshot",
    "CompoundSynSnapshot",
)

EXECUTOR_ALLOWED = ("search_compound_syn",)

PRELOAD_FORBIDDEN = (
    "ensure_compound_syn_cache",
    "build_compound_syn_cache",
    "build_compound_syn_tiers",
    "search_compound_syn",
)

PRELOAD_ALLOWED = ("ensure_compound_syn_snapshot", "preload_compound_syn_runtime_cache")


class TestCompoundSynSeam(unittest.TestCase):
    def test_executor_delegates_to_search_compound_syn(self):
        source = EXECUTOR_PATH.read_text(encoding="utf-8")
        for symbol in EXECUTOR_FORBIDDEN:
            with self.subTest(symbol=symbol):
                self.assertNotIn(symbol, source)
        for symbol in EXECUTOR_ALLOWED:
            with self.subTest(symbol=symbol):
                self.assertIn(symbol, source)

    def test_preload_only_builds_snapshot(self):
        source = PRELOAD_PATH.read_text(encoding="utf-8")
        for symbol in PRELOAD_FORBIDDEN:
            with self.subTest(symbol=symbol):
                self.assertNotIn(symbol, source)
        for symbol in PRELOAD_ALLOWED:
            with self.subTest(symbol=symbol):
                self.assertIn(symbol, source)


if __name__ == "__main__":
    unittest.main()

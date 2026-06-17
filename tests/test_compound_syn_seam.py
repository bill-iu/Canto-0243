"""接縫測試：近義複合候選規則僅在 registry 委派 domain。"""
from __future__ import annotations

import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
SOURCES_PATH = REPO_ROOT / "app" / "services" / "position_match" / "sources.py"
PRELOAD_PATH = REPO_ROOT / "app" / "startup" / "offline_preload.py"

SOURCES_FORBIDDEN = (
    "load_compound_synonyms",
    "_scan_morpheme_compounds",
    "synthesize_compound_literals",
    "build_compound_syn_snapshot",
    "ensure_compound_syn_snapshot",
    "CompoundSynSnapshot",
    "narrow_compound_syn_literals",
    "load_compound_antonyms",
)

SOURCES_ALLOWED = ("search_compound_syn", "search_compound_ant", "search_connective_compound")

PRELOAD_FORBIDDEN = (
    "ensure_compound_syn_cache",
    "build_compound_syn_cache",
    "build_compound_syn_tiers",
    "search_compound_syn",
)

PRELOAD_ALLOWED = (
    "ensure_compound_syn_snapshot",
    "preload_compound_syn_runtime_cache",
    "ensure_compound_ant_snapshot",
    "preload_compound_ant_runtime_cache",
)


class TestCompoundSynSeam(unittest.TestCase):
    def test_sources_delegates_to_domain_compound_search(self):
        source = SOURCES_PATH.read_text(encoding="utf-8")
        for symbol in SOURCES_FORBIDDEN:
            with self.subTest(symbol=symbol):
                self.assertNotIn(symbol, source)
        for symbol in SOURCES_ALLOWED:
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

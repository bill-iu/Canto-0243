"""接縫測試：main.py 不得直接編排離線啟動預載。"""
from __future__ import annotations

import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
MAIN_PATH = REPO_ROOT / "main.py"

FORBIDDEN = (
    "ensure_thesaurus_loaded",
    "ensure_lexicon_loaded",
    "ensure_rime_char_loaded",
    "ensure_essay_loaded",
    "ensure_curated_loaded",
    "ensure_compound_syn_cache",
    "bootstrap_local_db",
    "ensure_length_column",
    "start_word_cache_preload_background",
    "Base.metadata.create_all",
)

REQUIRED = (
    "run_lifespan_startup",
    "run_main_block_startup",
    "get_readiness_snapshot",
    "offline_preload",
)


class TestOfflinePreloadSeam(unittest.TestCase):
    def test_main_delegates_to_offline_preload(self):
        source = MAIN_PATH.read_text(encoding="utf-8")
        for symbol in FORBIDDEN:
            with self.subTest(symbol=symbol):
                self.assertNotIn(symbol, source)
        for symbol in REQUIRED:
            with self.subTest(symbol=symbol):
                self.assertIn(symbol, source)


if __name__ == "__main__":
    unittest.main()

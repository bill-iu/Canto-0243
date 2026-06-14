"""接縫測試：query_dispatch 不得洩漏缺字型查詢執行細節。"""
from __future__ import annotations

import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
DISPATCH_PATH = REPO_ROOT / "app" / "services" / "query_dispatch.py"

FORBIDDEN = (
    "build_match_spec",
    "CandidateSource",
    "run_position_query",
    "run_position_query_tracked",
    "mask_priority_key",
    "MaskWildcardCandidateSource",
    "LengthCodeCandidateSource",
    "LengthMaskCandidateSource",
    "RhymeAnchorCandidateSource",
    "_dispatch_position_query",
)

ALLOWED = (
    "execute_mask_family_search",
    "is_mask_family_query",
    "_mask_family_search_result",
)


class TestMaskFamilyDispatchSeam(unittest.TestCase):
    def test_query_dispatch_source_has_no_leaked_symbols(self):
        source = DISPATCH_PATH.read_text(encoding="utf-8")
        for symbol in FORBIDDEN:
            with self.subTest(symbol=symbol):
                self.assertNotIn(symbol, source)

    def test_query_dispatch_uses_single_mask_family_entry(self):
        source = DISPATCH_PATH.read_text(encoding="utf-8")
        for symbol in ALLOWED:
            with self.subTest(symbol=symbol):
                self.assertIn(symbol, source)


if __name__ == "__main__":
    unittest.main()

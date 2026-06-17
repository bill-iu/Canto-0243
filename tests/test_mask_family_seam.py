"""接縫測試：query_dispatch 不得洩漏缺字型查詢執行細節。"""
from __future__ import annotations

import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
DISPATCH_PATH = REPO_ROOT / "app" / "services" / "query_dispatch.py"

FORBIDDEN = (
    "build_match_spec",
    "build_equals_match_spec",
    "execute_mask_family_search",
    "CandidateSource",
    "run_position_query",
    "run_position_query_tracked",
    "literal_priority_sort_key",
    "MaskWildcardCandidateSource",
    "LengthCodeCandidateSource",
    "LengthMaskCandidateSource",
    "RhymeAnchorCandidateSource",
    "_dispatch_position_query",
    "anchor_dimension",
    "_dual_phoneme_anchor_search_result",
)

ALLOWED = (
    "execute_match_spec",
    "normalize_to_match_spec",
    "_mask_family_search_result",
    "route_kind_for",
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

    def test_query_dispatch_has_no_compound_handler_registry(self):
        source = DISPATCH_PATH.read_text(encoding="utf-8")
        self.assertNotIn("CompoundSynQuery", source)
        self.assertNotIn("CompoundAntQuery", source)


if __name__ == "__main__":
    unittest.main()

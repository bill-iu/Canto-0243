"""數字夾字 P2 — 刪 hybrid kinds、explain 碼夾／整詞分叉（ADR-0028）。"""
from __future__ import annotations

import unittest

from app.services.query_explain import explain_query
from app.services.query_parse import normalize_and_parse
from app.services.query_types import QueryKind


class CodeSandwichP2Tests(unittest.TestCase):
    def test_hybrid_kinds_removed(self):
        values = {k.value for k in QueryKind}
        self.assertNotIn("hybrid_code", values)
        self.assertNotIn("hybrid_tail_equals_alias", values)

    def test_23就_never_parses_hybrid(self):
        parsed = normalize_and_parse("23就")
        self.assertEqual(parsed.kind, QueryKind.EQUALS)

    def test_explain_23就_labels_code_sandwich(self):
        result = explain_query("23就")
        self.assertEqual(result.kind, "equals")
        self.assertIn("數字夾字", result.summary or "")
        self.assertNotIn("整詞", result.summary or "")

    def test_explain_香港_labels_whole_word(self):
        result = explain_query("香港=")
        self.assertIn("整詞", result.summary or "")
        self.assertNotIn("數字夾字", result.summary or "")

    def test_explain_left_code_whole_ref_is_code_sandwich(self):
        result = explain_query("0449窮困潦倒=")
        self.assertIn("數字夾字", result.summary or "")
        self.assertNotIn("整詞同", result.summary or "")


if __name__ == "__main__":
    unittest.main()
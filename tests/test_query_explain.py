"""查詢語意解釋 — server explain API (ADR-0021)."""
from __future__ import annotations

import unittest

from app.services.query_explain import explain_query


class QueryExplainTests(unittest.TestCase):
    def test_empty_query_returns_no_summary(self):
        result = explain_query("")
        self.assertIsNone(result.summary)
        self.assertIsNone(result.warning)
        self.assertIsNone(result.kind)

    def test_unmatched_shows_parser_hint_as_warning(self):
        result = explain_query("2+好+3")
        self.assertIsNone(result.summary)
        self.assertIsNotNone(result.warning)
        self.assertEqual(result.kind, "unmatched")

    def test_plus_anchor_rhyme_uses_char_position_wording(self):
        result = explain_query("23+好=")
        self.assertIn("三個字", result.summary or "")
        self.assertIn("第 3 個字", result.summary or "")
        self.assertIn("同韻", result.summary or "")
        self.assertIn("好", result.summary or "")
        self.assertEqual(result.kind, "plus_anchor")

    def test_mask_query_describes_literal_and_wildcards(self):
        result = explain_query("香??")
        self.assertIn("三個字", result.summary or "")
        self.assertIn("第 1 個字", result.summary or "")
        self.assertIn("香", result.summary or "")
        self.assertIn("任意字", result.summary or "")

    def test_23o_warns_about_23_plus_o(self):
        result = explain_query("23o")
        self.assertIn("兩個字", result.summary or "")
        self.assertIsNotNone(result.warning)
        self.assertIn("23+o", result.warning or "")

    def test_23_plus_o_warns_about_23o(self):
        result = explain_query("23+o")
        self.assertIn("三個字", result.summary or "")
        self.assertIsNotNone(result.warning)
        self.assertIn("23o", result.warning or "")

    def test_serial_phoneme_anchor_summary(self):
        result = explain_query("04困=49倒=")
        self.assertIn("四個字", result.summary or "")
        self.assertIn("第 2 個字", result.summary or "")
        self.assertIn("困", result.summary or "")
        self.assertIn("同韻", result.summary or "")

    def test_word_lookup_summary(self):
        result = explain_query("香港")
        self.assertIn("香港", result.summary or "")
        self.assertEqual(result.kind, "word_lookup")


if __name__ == "__main__":
    unittest.main()
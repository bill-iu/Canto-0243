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

    def test_hybrid_code_tail_ref_rhyme_summary(self):
        result = explain_query("23我")
        self.assertEqual(
            result.summary,
            "兩個字：第 1 個字同 2 同音，第 2 個字同 3 同音且同「我」同韻",
        )
        self.assertEqual(result.kind, "hybrid_code")

    def test_code_sandwich_equals_keeps_code_at_anchor_pos(self):
        result = explain_query("32我=0")
        self.assertEqual(
            result.summary,
            "三個字：第 1 個字同 3 同音，第 2 個字同 2 同音且同「我」同韻，第 3 個字同 0 同音",
        )
        self.assertEqual(result.kind, "equals")

    def test_23o_keeps_summary_and_warning(self):
        result = explain_query("23o")
        self.assertIn("兩個字", result.summary or "")
        self.assertIn("同韻母 o", result.summary or "")
        self.assertIsNotNone(result.warning)
        self.assertIn("23+o", result.warning or "")
        self.assertNotIn("此查詢為", result.warning or "")

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
        self.assertNotIn("串列錨", result.summary or "")

    def test_word_lookup_summary(self):
        result = explain_query("香港")
        self.assertIn("查詢詞條", result.summary or "")
        self.assertIn("香港", result.summary or "")
        self.assertEqual(result.kind, "word_lookup")

    def test_digit_code_summary(self):
        result = explain_query("23")
        self.assertEqual(result.summary, "查同23同音嘅字")
        self.assertEqual(result.kind, "digit_code")

    def test_equals_whole_word_rhyme_with_rhyme_label(self):
        result = explain_query("香港=")
        self.assertIn("整詞同「香港」同韻", result.summary or "")
        self.assertIn("雙押", result.summary or "")
        self.assertEqual(result.kind, "equals")

    def test_prefix_wildcard_equals_summary(self):
        result = explain_query("?香港=")
        self.assertIn("首個字任意", result.summary or "")
        self.assertIn("第 2、第 3 個字", result.summary or "")
        self.assertIn("同「香港」同韻", result.summary or "")
        self.assertIn("雙押", result.summary or "")
        self.assertEqual(result.kind, "prefix_wildcard_equals")

    def test_relation_synonym_lookup(self):
        result = explain_query("~開心")
        self.assertIn("查「開心」嘅近義詞", result.summary or "")
        self.assertNotIn("近義關係", result.summary or "")
        self.assertEqual(result.kind, "relation_lookup")


if __name__ == "__main__":
    unittest.main()
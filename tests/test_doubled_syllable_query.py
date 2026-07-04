"""雙聲疊韻字查詢 — parser 與比對契約。"""
from __future__ import annotations

import unittest

from app.domain.relations.compound_doubled_syllable import (
    row_has_doubled_syllables,
    row_has_uniform_syllable_letters,
)
from app.services.jyutping_anchor import normalize_hanzi_dollar_syllable_anchors
from app.services.query_parse import (
    CompoundDoubledSyllableQuery,
    UnmatchedQuery,
    normalize_and_parse,
)
from app.services.query_match_spec_registry import build_match_spec_for_parsed


class DoubledSyllableQueryTests(unittest.TestCase):
    def test_parse_width_from_dollar_run(self):
        parsed = normalize_and_parse("$$$")
        self.assertIsInstance(parsed, CompoundDoubledSyllableQuery)
        self.assertEqual(parsed.width, 3)

    def test_parse_rejects_code_width_mismatch(self):
        parsed = normalize_and_parse("33$$$")
        self.assertIsInstance(parsed, UnmatchedQuery)
        self.assertIn("碼位數", parsed.hint or "")

    def test_parse_rejects_too_many_dollars(self):
        parsed = normalize_and_parse("$$$$$")
        self.assertIsInstance(parsed, UnmatchedQuery)

    def test_normalize_preserves_dollar_run(self):
        self.assertEqual(normalize_hanzi_dollar_syllable_anchors("$$$你"), "$$$你")

    def test_uniform_syllable_rows(self):
        self.assertTrue(row_has_doubled_syllables("sik1 sik6"))
        self.assertTrue(row_has_uniform_syllable_letters("haa1 haa1 haa1", 3))
        self.assertFalse(row_has_uniform_syllable_letters("sik6 hou2 sik6", 3))

    def test_match_spec_rhyme_anchor_pos(self):
        spec = build_match_spec_for_parsed(normalize_and_parse("$$$你"))
        self.assertEqual(spec.width, 3)
        self.assertEqual(spec.slots[0].pos, 2)


if __name__ == "__main__":
    unittest.main()
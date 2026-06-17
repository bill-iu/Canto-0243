"""StarAnchorQuery — *{漢字} 家族（頭/中/尾格 + = 同韻母）。"""
from __future__ import annotations

import unittest

from app.services.query_parse import StarAnchorQuery, UnmatchedQuery, parse_query
from app.services.word_query_parser import normalize_search_query


def _parse(q: str):
    return parse_query(normalize_search_query(q))


class StarAnchorGoldenParseTests(unittest.TestCase):
    def test_tail_literal(self):
        parsed = _parse("23*就")
        self.assertIsInstance(parsed, StarAnchorQuery)
        self.assertEqual(parsed.width, 3)
        self.assertEqual(parsed.anchor_pos, 2)
        self.assertEqual(parsed.anchor, "就")
        self.assertEqual(parsed.constraint, "literal")
        self.assertEqual(parsed.code_prefix, "23")
        self.assertEqual(parsed.code_slots, [(0, "2"), (1, "3")])

    def test_tail_rhyme_final(self):
        parsed = _parse("23*就=")
        self.assertIsInstance(parsed, StarAnchorQuery)
        self.assertEqual(parsed.constraint, "final")

    def test_tail_initial_legacy(self):
        parsed = _parse("23*=就")
        self.assertIsInstance(parsed, StarAnchorQuery)
        self.assertEqual(parsed.constraint, "initial")

    def test_middle_literal(self):
        parsed = _parse("2*就3")
        self.assertIsInstance(parsed, StarAnchorQuery)
        self.assertEqual(parsed.width, 3)
        self.assertEqual(parsed.anchor_pos, 1)
        self.assertEqual(parsed.anchor, "就")
        self.assertEqual(parsed.constraint, "literal")
        self.assertEqual(parsed.code_prefix, None)
        self.assertEqual(parsed.code_slots, [(0, "2"), (2, "3")])

    def test_middle_rhyme_final(self):
        parsed = _parse("2*就=3")
        self.assertIsInstance(parsed, StarAnchorQuery)
        self.assertEqual(parsed.constraint, "final")

    def test_head_literal(self):
        parsed = _parse("*門0")
        self.assertIsInstance(parsed, StarAnchorQuery)
        self.assertEqual(parsed.width, 2)
        self.assertEqual(parsed.anchor_pos, 0)
        self.assertEqual(parsed.anchor, "門")
        self.assertEqual(parsed.constraint, "literal")
        self.assertEqual(parsed.code_slots, [(1, "0")])

    def test_head_rhyme_final(self):
        parsed = _parse("*門=0")
        self.assertIsInstance(parsed, StarAnchorQuery)
        self.assertEqual(parsed.constraint, "final")


class StarAnchorHintTests(unittest.TestCase):
    def test_middle_equals_wrong_side_triggers_hint(self):
        parsed = _parse("2*=就3")
        self.assertIsInstance(parsed, UnmatchedQuery)
        self.assertTrue(parsed.hint)
        self.assertIn("2*就=3", parsed.hint)

    def test_head_equals_wrong_side_triggers_hint(self):
        parsed = _parse("*門0=")
        self.assertIsInstance(parsed, UnmatchedQuery)
        self.assertTrue(parsed.hint)
        self.assertIn("*門=0", parsed.hint)

    def test_head_missing_right_code_triggers_hint(self):
        parsed = _parse("*門")
        self.assertIsInstance(parsed, UnmatchedQuery)
        self.assertTrue(parsed.hint)
        self.assertIn("*門0", parsed.hint)


if __name__ == "__main__":
    unittest.main()


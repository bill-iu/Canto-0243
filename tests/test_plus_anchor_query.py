"""PlusAnchorQuery — +{漢字} 家族（頭/中/尾格 + = 同韻母）。"""
import unittest

from app.services.query_lexer import normalize_search_query
from app.services.query_parse import MaskQuery, PlusAnchorQuery, UnmatchedQuery, parse_query


def _parse(q: str):
    return parse_query(normalize_search_query(q))


class PlusAnchorNormalizeTests(unittest.TestCase):
    def test_legacy_star_alias_to_plus(self):
        self.assertEqual(normalize_search_query("23*就"), "23+就")

    def test_fullwidth_plus_and_star(self):
        self.assertEqual(normalize_search_query("23＋就"), "23+就")
        self.assertEqual(normalize_search_query("23＊就"), "23+就")


class PlusAnchorGoldenParseTests(unittest.TestCase):
    def test_code_tail_literal(self):
        parsed = _parse("23+就")
        self.assertIsInstance(parsed, PlusAnchorQuery)
        self.assertEqual(parsed.width, 3)
        self.assertEqual(parsed.constraint, "literal")
        self.assertEqual(parsed.anchor, "就")
        self.assertEqual(parsed.anchor_pos, 2)
        self.assertEqual(parsed.code_prefix, "23")

    def test_legacy_star_input(self):
        self.assertIsInstance(_parse("23*就"), PlusAnchorQuery)

    def test_code_tail_final(self):
        parsed = _parse("23+就=")
        self.assertIsInstance(parsed, PlusAnchorQuery)
        self.assertEqual(parsed.constraint, "final")

    def test_code_tail_initial(self):
        parsed = _parse("23+=就")
        self.assertIsInstance(parsed, PlusAnchorQuery)
        self.assertEqual(parsed.constraint, "initial")

    def test_middle_literal(self):
        parsed = _parse("2+就3")
        self.assertIsInstance(parsed, PlusAnchorQuery)
        self.assertEqual(parsed.width, 3)
        self.assertEqual(parsed.anchor_pos, 1)
        self.assertEqual(parsed.constraint, "literal")

    def test_middle_final(self):
        parsed = _parse("2+就=3")
        self.assertIsInstance(parsed, PlusAnchorQuery)
        self.assertEqual(parsed.constraint, "final")

    def test_head_literal_via_mask(self):
        parsed = _parse("+門0")
        self.assertIsInstance(parsed, MaskQuery)

    def test_head_plus_anchor_final(self):
        parsed = _parse("+門=0")
        self.assertIsInstance(parsed, PlusAnchorQuery)
        self.assertEqual(parsed.constraint, "final")


class PlusAnchorHintTests(unittest.TestCase):
    def test_equals_not_adjacent_hint(self):
        parsed = _parse("2+=就3")
        self.assertIsInstance(parsed, UnmatchedQuery)
        self.assertIn("2+就=3", parsed.hint)


if __name__ == "__main__":
    unittest.main()

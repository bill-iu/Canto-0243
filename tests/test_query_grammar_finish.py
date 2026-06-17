"""#3 收尾：wca／mask／relation grammar 公開行為。"""
from __future__ import annotations

import unittest

from app.services.query_parse import MaskQuery, RelationLookupQuery, parse_query
from app.services.query_lexer import normalize_search_query


def _parse(q: str):
    return parse_query(normalize_search_query(q))


class QueryGrammarWcaTests(unittest.TestCase):
    def test_wildcard_code_anchor_query(self):
        from app.services.query_grammar.wca import parse_wildcard_code_anchor_query

        parsed = parse_wildcard_code_anchor_query("?30人")
        self.assertIsNotNone(parsed)
        self.assertEqual(parsed["width"], 3)


class QueryGrammarMaskTests(unittest.TestCase):
    def test_looks_like_mask_query(self):
        from app.services.query_grammar.mask import looks_like_mask_query

        self.assertTrue(looks_like_mask_query("門0"))
        self.assertFalse(looks_like_mask_query("~開心"))

    def test_mask_query_via_facade(self):
        from app.services.word_query_parser import parse_mask_query

        width, codes, literals = parse_mask_query("門0")
        self.assertEqual(width, 2)
        self.assertEqual(codes[1], "0")


class QueryGrammarRelationTests(unittest.TestCase):
    def test_relation_lookup_via_parse(self):
        parsed = _parse("~開心")
        self.assertIsInstance(parsed, RelationLookupQuery)
        self.assertEqual(parsed.word, "開心")

    def test_mask_classified(self):
        parsed = _parse("香？？")
        self.assertIsInstance(parsed, MaskQuery)


class WordQueryParserFacadeTests(unittest.TestCase):
    def test_facade_is_reexport_only(self):
        from pathlib import Path

        source = (
            Path(__file__).resolve().parents[1]
            / "app"
            / "services"
            / "word_query_parser.py"
        ).read_text(encoding="utf-8")
        self.assertNotIn("def parse_", source)
        self.assertNotIn("def _wca", source)

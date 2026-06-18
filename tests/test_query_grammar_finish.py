"""#3 收尾：wca／mask／relation grammar 公開行為。"""
from __future__ import annotations

import unittest

from app.services.query_parse import MaskQuery, RelationLookupQuery, parse_query, try_parse_before_mask
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

    def test_mask_query_via_grammar(self):
        from app.services.query_grammar.mask import parse_mask_query

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

    def test_looks_like_mask_agrees_with_parse_chain(self):
        from app.services.query_grammar.mask import looks_like_mask_query

        for q in ("?30人", "就=", "23就", "~開心"):
            with self.subTest(q=q, rule="not_mask"):
                nq = normalize_search_query(q)
                self.assertFalse(looks_like_mask_query(nq))
                self.assertNotIsInstance(parse_query(nq), MaskQuery)

        for q in ("12香3", "2?3"):
            with self.subTest(q=q, rule="mask_fallback"):
                nq = normalize_search_query(q)
                self.assertTrue(looks_like_mask_query(nq))
                self.assertIsNone(try_parse_before_mask(nq))
                self.assertIsInstance(parse_query(nq), MaskQuery)

        for q in ("門0", "香？？"):
            with self.subTest(q=q, rule="mask_via_earlier_grammar"):
                nq = normalize_search_query(q)
                self.assertFalse(looks_like_mask_query(nq))
                self.assertIsInstance(parse_query(nq), MaskQuery)


class QueryGrammarFacadeRemovedTests(unittest.TestCase):
    def test_word_query_parser_module_removed(self):
        from pathlib import Path

        path = (
            Path(__file__).resolve().parents[1]
            / "app"
            / "services"
            / "word_query_parser.py"
        )
        self.assertFalse(path.is_file())
